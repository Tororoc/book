# -*- coding: utf-8 -*-
import os

from pm25_map_common import hour_cols, load_base_layers, read_pm25_station_data, render_pm25_map


# 输出路径可按需要修改
output_folder = r'D:\PM2.5影响分析\站点平均浓度分布图'


def calculate_station_mean(station_frames):
    """计算每个站点全部日期、全部小时的 PM2.5 平均浓度。"""
    station_mean = {}
    for station_name, frame in station_frames.items():
        value = frame[hour_cols].stack().mean(skipna=True)
        if value == value:
            station_mean[station_name] = value
    return station_mean


def main():
    print('正在读取并处理 PM2.5 数据...')
    station_frames = read_pm25_station_data()
    if not station_frames:
        raise RuntimeError('未读取到可用 PM2.5 数据，请检查 Excel 文件夹、sheet 名称和 00-23 小时列。')

    station_mean = calculate_station_mean(station_frames)
    base_layers = load_base_layers()

    out_path = os.path.join(output_folder, 'PM25_站点平均浓度分布图.png')
    render_pm25_map(station_mean, base_layers, out_path)
    print(f'完成：{out_path}')


if __name__ == '__main__':
    main()

