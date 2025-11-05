# ==============================================================================
# OpenPIVを用いた、動画からの流体速度場解析
# 各フレームペアの解析結果を画像として保存する
# ==============================================================================

# 必要なライブラリをインポート
import cv2
import numpy as np
import matplotlib.pyplot as plt
import pathlib
import argparse
import json
import os

# --- OpenPIVモジュールのインポート ---
try:
  from openpiv import process
  print("Successfully imported optimized 'process' module.")
except ImportError:
  print("Warning: Could not import optimized 'process' module. Falling back to 'pyprocess'.")
  print("For better performance, please ensure OpenPIV was installed correctly with its Cython extensions.")
  from openpiv import pyprocess as process

from openpiv import validation, filters, scaling, tools


def analyze_and_save_frames(video_path, output_dir, scaling_factor, vmax_override=None, frame_comparison_step=1, moving_average_window=1, averaging_method="mean"):
  """
  煙の動画をPIV解析し、指定されたフレーム間隔ごとの速度場を可視化して画像として保存する関数。
  オプションで、連続するフレームペアの解析結果を移動平均または移動中央値で集計し、滑らかなベクトル場を生成する。

  Args:
    video_path (str): 解析対象の動画ファイルへのパス。
    output_dir (str): 結果を保存するディレクトリ名。
    scaling_factor (float): スケーリング係数 (pixels/mm or pixels/unit)。
    vmax_override (float, optional): カラーマップの最大値を手動で指定。Noneの場合は自動計算。
    frame_comparison_step (int): 比較するフレームの間隔。デフォルトは1。
    moving_average_window (int): 移動集計のウィンドウサイズ。デフォルトは1（集計なし）。
    averaging_method (str): 集計方法（'mean'または'median'）。デフォルトは'mean'。
  """
  # --- 1. 初期設定と準備 ---
  print(f"--- Starting PIV Analysis for '{video_path}' ---")
  print(f"Parameters: Frame Step={frame_comparison_step}, Window={moving_average_window}, Method={averaging_method}")

  output_path = pathlib.Path(output_dir)
  output_path.mkdir(parents=True, exist_ok=True)

  cap = cv2.VideoCapture(video_path)
  if not cap.isOpened():
    print(f"Error: Could not open video file {video_path}")
    return

  fps = cap.get(cv2.CAP_PROP_FPS)
  if fps == 0:
    print("Warning: Could not get FPS from video. Assuming 30 FPS.")
    fps = 30.0
  dt = frame_comparison_step / fps

  # PIVパラメータ
  winsize = 32
  searchsize = 64
  overlap = 16
  sn_threshold = 1.1
  std_threshold = 3.0

  # --- 2. 1stパス: 解析とデータ収集 ---
  print("--- Pass 1: Analyzing all individual pairs and finding max velocity ---")
  
  frames_data = []
  overall_max_mag = 0.0
  
  frame_buffer = []
  for _ in range(frame_comparison_step + 1):
    ret, frame = cap.read()
    if ret:
      frame_buffer.append(frame)

  if len(frame_buffer) <= frame_comparison_step:
    print("Error: Not enough frames for the given frame_comparison_step.")
    cap.release()
    return

  x, y = None, None
  frame_index = 0

  while True:
    frame_a_color = frame_buffer[0]
    frame_b_color = frame_buffer[frame_comparison_step]
    
    frame_index += 1
    print(f"Analyzing frame pair starting at frame {frame_index}... ", end='\r')

    frame_a = cv2.cvtColor(frame_a_color, cv2.COLOR_BGR2GRAY)
    frame_b = cv2.cvtColor(frame_b_color, cv2.COLOR_BGR2GRAY)
    
    u, v, sig2noise = process.extended_search_area_piv(
      frame_a.astype(np.int32), frame_b.astype(np.int32),
      window_size=winsize, overlap=overlap, dt=dt,
      search_area_size=searchsize, sig2noise_method='peak2peak'
    )

    if x is None:
      x, y = process.get_coordinates(
        image_size=frame_a.shape, search_area_size=searchsize, overlap=overlap
      )

    mask_sn = validation.sig2noise_val(sig2noise, threshold=sn_threshold)
    mask_glob = validation.global_std(u, v, std_threshold=std_threshold)
    invalid_mask = np.logical_or(mask_sn, mask_glob)
    
    u_filtered, v_filtered = filters.replace_outliers(
      u, v, invalid_mask, method='localmean', max_iter=5, kernel_size=3
    )
    
    frames_data.append({
      "u": u_filtered, "v": v_filtered,
      "bg": frame_a_color.copy(),
      "frame_index": frame_index
    })

    _, _, u_scaled_tmp, v_scaled_tmp = scaling.uniform(x, y, u_filtered, v_filtered, scaling_factor=scaling_factor)
    magnitude = np.sqrt(u_scaled_tmp**2 + v_scaled_tmp**2)
    current_max_mag = np.nanmax(np.nan_to_num(magnitude))
    if current_max_mag > overall_max_mag:
      overall_max_mag = current_max_mag

    frame_buffer.pop(0)
    ret, new_frame = cap.read()
    if not ret:
      break
    frame_buffer.append(new_frame)

  cap.release()
  print(f"\nAnalysis of {len(frames_data)} pairs complete. Overall max magnitude: {overall_max_mag:.2f}")

  if not frames_data:
    print("No frames were analyzed.")
    return

  # --- 3. 2ndパス: 可視化と保存 ---
  print(f"--- Pass 2: Saving frames (Window: {moving_average_window}, Method: {averaging_method}) ---")
  
  vmax_to_use = overall_max_mag
  if vmax_override is not None:
    print(f"Using manual vmax override: {vmax_override}")
    vmax_to_use = vmax_override

  unit = "pixels" if scaling_factor == 1.0 else "mm"

  x_scaled, y_scaled, _, _ = scaling.uniform(x, y, frames_data[0]["u"], frames_data[0]["v"], scaling_factor=scaling_factor)

  num_images_to_save = len(frames_data) - moving_average_window + 1
  for i in range(num_images_to_save):
    
    window_data = frames_data[i : i + moving_average_window]
    base_data = window_data[0]
    frame_num = base_data["frame_index"]

    print(f"Processing and saving image {i+1}/{num_images_to_save} (starts at frame {frame_num})... ", end='\r')

    u_arrays = [d["u"] for d in window_data]
    v_arrays = [d["v"] for d in window_data]
    
    if averaging_method == 'median':
      aggregated_u_raw = np.nanmedian(np.stack(u_arrays), axis=0)
      aggregated_v_raw = np.nanmedian(np.stack(v_arrays), axis=0)
    else:
      aggregated_u_raw = np.nanmean(np.stack(u_arrays), axis=0)
      aggregated_v_raw = np.nanmean(np.stack(v_arrays), axis=0)

    _, _, agg_u_scaled, agg_v_scaled = scaling.uniform(x, y, aggregated_u_raw, aggregated_v_raw, scaling_factor=scaling_factor)

    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(cv2.cvtColor(base_data["bg"], cv2.COLOR_BGR2RGB), alpha=0.8)
    
    magnitude = np.sqrt(agg_u_scaled**2 + agg_v_scaled**2)
    
    magnitude_nonan = np.nan_to_num(magnitude)
    agg_u_nonan = np.nan_to_num(agg_u_scaled)
    agg_v_nonan = np.nan_to_num(agg_v_scaled)

    plot_scale = vmax_to_use * 20 if vmax_to_use > 0 else 30

    quiver = ax.quiver(
      x_scaled, y_scaled, agg_u_nonan, -agg_v_nonan,
      magnitude_nonan,
      cmap='viridis',
      scale=plot_scale,
      width=0.0035,
      headwidth=3,
      headlength=5
    )
    quiver.set_clim(vmin=0, vmax=vmax_to_use)

    cbar = plt.colorbar(quiver, ax=ax, shrink=0.8)
    cbar.set_label(f'Velocity Magnitude ({unit}/s)')

    ax.set_xlabel(f'X ({unit})')
    ax.set_ylabel(f'Y ({unit})')
    
    title = f'Velocity Field (Frame {frame_num} to {frame_num + frame_comparison_step})'
    if moving_average_window > 1:
      method_name = "Median" if averaging_method == 'median' else "Averaged"
      title = f'{method_name} Velocity Field (Window: {moving_average_window}, Start Frame: {frame_num})'
    ax.set_title(title)
    
    output_plot_path = output_path / f'img{frame_num:003d}.png'
    plt.savefig(output_plot_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

  print(f"\n\nProcessing complete. Saved {num_images_to_save} images to '{output_dir}'.")
  print("--- Analysis Finished ---")

# --- スクリプトの実行 ---
if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Analyze a video with PIV using settings from a JSON config file.")
  parser.add_argument("--config", help="Specify which execution configuration to use from execData.jsonc.")
  args = parser.parse_args()

  # 設定ファイルを読み込む
  # スクリプトの場所を基準に `execData.jsonc` を探す
  script_dir = os.path.dirname(os.path.abspath(__file__))
  config_path = os.path.join(script_dir, '..', 'execData.jsonc')

  try:
    with open(config_path, 'r') as f:
      # remove comments from jsonc
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

  piv_params = execution_params.get("piv_analysis")
  if not piv_params:
    print(f"Error: 'piv_analysis' section not found for configuration '{config_key}'.")
    exit()

  analyze_and_save_frames(
    video_path=piv_params.get("video_path"),
    output_dir=piv_params.get("output_dir"),
    scaling_factor=piv_params.get("scaling_factor", 1.0),
    vmax_override=piv_params.get("vmax"),
    frame_comparison_step=piv_params.get("frame_comparison_step", 1),
    moving_average_window=piv_params.get("moving_average_window", 1),
    averaging_method=piv_params.get("averaging_method", "mean")
  )
