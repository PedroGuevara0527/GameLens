# player_backend.py
# Updated backend for Flask integration

import time
import pandas as pd
from PIL import Image
from google import genai
from nba_api.stats.endpoints import (
    playergamelog,
    playercareerstats,
    commonplayerinfo
)
from nba_api.stats.static import players

# Gemini client
# NOTE: The API key here is an example and should be retrieved securely in a real application.
client = genai.Client(api_key="AIzaSyD-jnak65x-Wva2PdSVWCx9Vf3dJLjZjS8")

CURRENT_SEASON = '2025-26'


def get_player_info(image_path, sport):
    """
    Given an image path and sport (e.g., 'NBA'),
    return a dictionary with the statistical summary and the Instagram caption
    as two separate fields.
    """

    # Helper function for structured error return
    def error_response(msg):
        return {"status": "error", "message": msg}

    if sport.upper() != "NBA":
        return error_response(f"Support for {sport} is not yet implemented.")

    try:
        # --- Player Identification ---
        image = Image.open(image_path)
        player_resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=["Only tell me the full name of the player who is making the play in this image", image]
        )
        player = player_resp.text.strip()

        # --- Get Player ID ---
        nba_players = players.get_players()
        player_id = None
        for p in nba_players:
            if p['full_name'].lower() == player.lower():
                player_id = p['id']
                break

        if player_id is None:
            return error_response(f"Player '{player}' not found in NBA database.")

        # --- Find TEAM player is on ---
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        time.sleep(0.5)
        player_dict = player_info.get_normalized_dict()

        if not player_dict.get('CommonPlayerInfo'):
            return error_response(f"Could not retrieve team info for {player}.")

        info = player_dict['CommonPlayerInfo'][0]
        team_name = info.get('TEAM_NAME', 'Unknown Team')

        # --- Get Latest Game Stats ---
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=CURRENT_SEASON)
        time.sleep(0.5)
        gamelog_df = gamelog.get_data_frames()[0]

        latest_game_text = ""
        game_stats = {}

        if gamelog_df.empty:
            latest_game_text = f"No recent games found for the {CURRENT_SEASON} season."
        else:
            latest_game_stats = gamelog_df.iloc[0]
            game_stats = {
                'Date': latest_game_stats['GAME_DATE'],
                'Opponent': latest_game_stats['MATCHUP'],
                'Result (W/L)': latest_game_stats['WL'],
                'Minutes': latest_game_stats['MIN'],
                'Points': latest_game_stats['PTS'],
                'Rebounds': latest_game_stats['REB'],
                'Assists': latest_game_stats['AST'],
            }
            latest_game_text = (
                f"In their most recent game on {game_stats['Date']} ({game_stats['Opponent']}), "
                f"they scored {game_stats['Points']} points, grabbed {game_stats['Rebounds']} rebounds, "
                f"and made {game_stats['Assists']} assists in {game_stats['Minutes']} minutes."
            )

        # --- Get Career Stats ---
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id, per_mode36='PerGame')
        time.sleep(0.5)
        career_df = career_stats.get_data_frames()[0]
        career_rows = career_df[career_df['SEASON_ID'] == 'Career']

        if not career_rows.empty:
            career_row = career_rows.iloc[0]
            avg_pts = career_row['PTS']
            avg_ast = career_row['AST']
            avg_reb = career_row['REB']
            avg_fg = career_row['FG_PCT']
            avg_3pt = career_row['FG3_PCT']
            avg_ft = career_row['FT_PCT']
            season_stats = { # Initialize season_stats with career data for the prompt
                "avg_player_points": avg_pts,
                "avg_player_assists": avg_ast,
                "avg_player_rebounds": avg_reb,
                "avg_player_field": avg_fg,
                "avg_player_three": avg_3pt,
                "avg_player_free": avg_ft,
            }
        else:
            # Fallback to calculating the mean of all seasons
            season_df = career_df[career_df['SEASON_ID'] != 'Career'] 
            
            if season_df.empty:
                return error_response(f"Could not retrieve any career season data for {player}.")
            
            # Calculate means and cast them to standard Python floats for formatting
            avg_pts = float(season_df['PTS'].mean())
            avg_ast = float(season_df['AST'].mean())
            avg_reb = float(season_df['REB'].mean())
            avg_fg = float(season_df['FG_PCT'].mean())
            avg_3pt = float(season_df['FG3_PCT'].mean())
            avg_ft = float(season_df['FT_PCT'].mean())

            season_stats = {
                "avg_player_points": avg_pts,
                "avg_player_assists": avg_ast,
                "avg_player_rebounds": avg_reb,
                "avg_player_field": avg_fg,
                "avg_player_three": avg_3pt,
                "avg_player_free": avg_ft,
            }
        
        # --- Generate Instagram-style Caption with Gemini ---
        # NOTE: Using repr() on the dictionary ensures the prompt sees the data structure clearly
        caption_resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                f"Write a short, Instagram-style caption describing what is going on in this image and comparing the player's career averages {repr(season_stats)} to their latest game stats {repr(game_stats)}. Keep the output short and enthusiastic.", 
                image
            ]
        )
        caption = caption_resp.text.strip()

        # --- Create Two Separate Output Messages ---
        stats_summary = (
            f"{player} currently plays for the {team_name}. "
            f"{latest_game_text} "
            f"Throughout their career, they’ve averaged {avg_pts:.1f} points, "
            f"{avg_reb:.1f} rebounds, and {avg_ast:.1f} assists per game, "
            f"shooting {avg_fg:.3f} from the field, {avg_3pt:.3f} from three, and {avg_ft:.3f} from the line."
        )

        caption_output = f"Instagram Caption: {caption}"

        # Return a dictionary with the structured output
        return {
            "status": "success",
            "stats_summary": stats_summary,
            "caption_output": caption_output
        }

    except Exception as e:
        return error_response(f"Error generating player info: {e}")
