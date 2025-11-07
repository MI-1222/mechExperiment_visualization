# ==============================================================================
# PIV解析と動画生成のパイプライン統括スクリプト
#
# 概要:
#   - `execData.jsonc` ファイルから実行設定を読み込む。
#   - コマンドライン引数 `--config` で使用する設定を指定できる。
#   - 指定された設定に基づき、PIV解析と動画生成の処理を順次実行する。
#
# 実行方法:
#   - デフォルト設定で実行: `python src/main.py`
#   - 特定の設定で実行: `python src/main.py --config test03`
# ==============================================================================

import argparse
import json
import os
import re
import sys

# --- モジュール検索パスの設定 ---
# スクリプトの場所を基準にプロジェクトルートを`sys.path`に追加する。
# これにより、`src` パッケージ内のモジュール (`piv_analysis`, `create_video`) を
# 正しくインポートできるようになる。
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

# --- 内部モジュールのインポート ---
from src.lib.open_piv import piv_analysis
from src.utils import create_video

def main():
  """
  PIV解析と動画生成のパイプラインを統括するメイン関数。
  `execData.jsonc` から設定を読み込み、指定された処理を実行する。
  """
  # --- 1. コマンドライン引数の解析 ---
  # --config: 使用する実行設定キーを `execData.jsonc` から指定する。
  parser = argparse.ArgumentParser(
    description="Run PIV analysis and video creation pipeline based on a JSON config file.",
    formatter_class=argparse.RawTextHelpFormatter
  )
  parser.add_argument(
    "--config",
    help="Specify which execution configuration key to use from execData.jsonc.\n" \
       "If not provided, the 'execution_key' from 'default_execution' will be used."
  )
  args = parser.parse_args()

  # --- 2. 設定ファイル (execData.jsonc) の読み込み ---
  config_path = os.path.join(project_root, 'src', 'execData.jsonc')
  try:
    with open(config_path, 'r', encoding='utf-8') as f:
      # JSONC形式（コメント付きJSON）をパースするため、正規表現でコメント行を削除
      json_str = re.sub(r'//.*\n', '\n', f.read())
      config_data = json.loads(json_str)
  except FileNotFoundError:
    print(f"Error: Configuration file not found at {config_path}")
    sys.exit(1)
  except json.JSONDecodeError as e:
    print(f"Error: Could not decode JSON from {config_path}. Details: {e}")
    sys.exit(1)

  # --- 3. 実行キーの決定 ---
  # コマンドライン引数 `--config` があればそれを使い、なければデフォルト値を使用する。
  if args.config:
    config_key = args.config
  else:
    try:
      config_key = config_data["default_execution"]["execution_key"]
    except KeyError:
      print("Error: No --config specified and 'default_execution' or 'execution_key' not found in config file.")
      sys.exit(1)
  
  print(f"========================================")
  print(f"Using execution configuration: '{config_key}'")
  print(f"========================================")

  # --- 4. 実行パラメータと実行フラグの取得 ---
  try:
    # 指定されたキーに対応する設定を取得
    execution_params = config_data["executions"][config_key]
    # 個別の実行設定に `execution_function` があればそれを使い、なければデフォルト設定を使用
    exec_flags = execution_params.get("execution_function", config_data["default_execution"]["execution_function"])
  except KeyError:
    print(f"Error: Configuration key '{config_key}' not found in 'executions' section of execData.jsonc.")
    sys.exit(1)

  # --- 5. PIV解析の実行 ---
  # `exec_flags` に基づいて処理を実行するか判断
  if exec_flags.get("piv_analysis", False):
    print("\n--- Initiating PIV Analysis ---")
    try:
      piv_params = execution_params["piv_analysis"]
      # 設定ファイル内の相対パスを、プロジェクトルートからの絶対パスに変換
      video_path = os.path.join(project_root, piv_params["video_path"])
      output_dir = os.path.join(project_root, piv_params["output_dir"])

      # PIV解析関数を呼び出し
      piv_analysis.analyze_and_save_frames(
        video_path=video_path,
        output_dir=output_dir,
        scaling_factor=piv_params.get("scaling_factor", 1.0),
        vmax_override=piv_params.get("vmax"),
        frame_comparison_step=piv_params.get("frame_comparison_step", 1),
        moving_average_window=piv_params.get("moving_average_window", 1),
        averaging_method=piv_params.get("averaging_method", "mean"),
        piv_params=piv_params.get("piv_parameters", {})
      )
    except KeyError as e:
      print(f"Error: Missing required parameter {e} in 'piv_analysis' for '{config_key}'.")
      sys.exit(1)
    except Exception as e:
      print(f"An unexpected error occurred during PIV analysis: {e}")
      sys.exit(1)
  else:
    print("\nSkipping PIV Analysis as per configuration.")

  # --- 6. 動画生成の実行 ---
  # `exec_flags` に基づいて処理を実行するか判断
  if exec_flags.get("create_video", False):
    print("\n--- Initiating Video Creation ---")
    try:
      # PIV解析の出力ディレクトリを、動画生成の入力画像フォルダとして使用
      image_folder = os.path.join(project_root, execution_params["piv_analysis"]["output_dir"])
      video_params = execution_params["create_video"]
      output_folder = os.path.join(project_root, video_params["output_dir"])

      # 動画生成関数を呼び出し
      create_video.create_video_from_images(
        image_folder=image_folder,
        output_folder=output_folder,
        fps=video_params.get("fps", 30),
        image_pattern=video_params.get("pattern", 'img*.png'),
        output_filename=video_params.get("name")
      )
    except KeyError as e:
      print(f"Error: Missing required parameter {e} in 'create_video' or 'piv_analysis' for '{config_key}'.")
      sys.exit(1)
    except Exception as e:
      print(f"An unexpected error occurred during video creation: {e}")
      sys.exit(1)
  else:
    print("\nSkipping Video Creation as per configuration.")

  print("\n========================================")
  print("Pipeline finished.")
  print("========================================")

if __name__ == '__main__':
  # このスクリプトが直接実行された場合に main() 関数を呼び出す
  main()