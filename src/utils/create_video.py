import cv2
import os
import glob
import datetime
import argparse
import json

def create_video_from_images(image_folder, output_folder, fps=30, image_pattern='img*.png', output_filename=None):
  """
  指定されたフォルダ内の画像からMP4動画を作成する関数

  Args:
    image_folder (str): 画像が保存されている入力フォルダのパス
    output_folder (str): 動画を保存する出力フォルダのパス
    fps (int): 動画のフレームレート
    image_pattern (str): 読み込む画像のファイル名パターン (例: 'img*.png')
    output_filename (str, optional): 出力する動画のファイル名。指定しない場合はタイムスタンプ付きのファイル名が自動生成される。
  """
  os.makedirs(output_folder, exist_ok=True)

  image_files = sorted(glob.glob(os.path.join(image_folder, image_pattern)))

  if not image_files:
    print(f"エラー: '{image_folder}' にパターン '{image_pattern}' でマッチする画像が見つかりません。")
    return

  print(f"{len(image_files)} 個の画像ファイルを読み込みます。")

  try:
    frame = cv2.imread(image_files[0])
    height, width, layers = frame.shape
    size = (width, height)
  except Exception as e:
    print(f"エラー: 最初の画像 '{image_files[0]}' の読み込みに失敗しました。{e}")
    return

  print(f"動画サイズ: {width}x{height}, FPS: {fps}")

  if output_filename:
    video_name = os.path.join(output_folder, output_filename)
  else:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_name = os.path.join(output_folder, f"video_{timestamp}.mp4")

  fourcc = cv2.VideoWriter_fourcc(*'mp4v')
  video = cv2.VideoWriter(video_name, fourcc, fps, size)

  for i, image_file in enumerate(image_files):
    frame = cv2.imread(image_file)
    if frame is not None:
      video.write(frame)
      print(f"\rフレームを処理中... {i + 1}/{len(image_files)}", end="")
    else:
      print(f"\n警告: '{image_file}' の読み込みに失敗しました。スキップします。")

  video.release()
  print(f"\n\n✅ 動画の作成が完了しました！\n   -> {video_name}")

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Create a video from a sequence of images using settings from a JSON config file.")
  parser.add_argument("--config", help="Specify which execution configuration to use from execData.jsonc.")
  args = parser.parse_args()

  # 設定ファイルを読み込む
  script_dir = os.path.dirname(os.path.abspath(__file__))
  config_path = os.path.join(script_dir, '..', 'execData.jsonc')

  try:
    with open(config_path, 'r') as f:
      import re
      json_str = re.sub(r'//.*\n', '\n', f.read())
      config_data = json.loads(json_str)
  except FileNotFoundError:
    print(f"Error: Configuration file not found at {config_path}")
    exit()
  except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from {config_path}")
    exit()

  # 使用する設定キーを決定
  config_key = args.config if args.config else config_data.get("default_execution")
  if not config_key:
    print("Error: No configuration specified and no default_execution found in config file.")
    exit()

  print(f"Using configuration: '{config_key}'")

  # 設定を取得
  execution_params = config_data.get("executions", {}).get(config_key)
  if not execution_params:
    print(f"Error: Configuration '{config_key}' not found in execData.jsonc.")
    exit()

  piv_params = execution_params.get("piv_analysis", {})
  video_params = execution_params.get("create_video", {})
  
  # PIV解析の出力ディレクトリを動画生成の入力ディレクトリとして使用
  image_folder = piv_params.get("output_dir")
  if not image_folder:
    print(f"Error: 'output_dir' not found in 'piv_analysis' section for configuration '{config_key}'.")
    exit()

  print("--- 動画生成スクリプト開始 ---")
  create_video_from_images(
    image_folder=image_folder,
    output_folder=video_params.get("output_dir", os.path.join('output', 'video')),
    fps=video_params.get("fps", 30),
    image_pattern=video_params.get("pattern", 'img*.png'),
    output_filename=video_params.get("name")
  )
  print("--- 処理終了 ---")