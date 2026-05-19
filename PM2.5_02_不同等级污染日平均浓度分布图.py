# -*- coding: utf-8 -*-
import os

from pm25_map_common import (
    get_daily_mean,
    get_grade_mask,
    load_base_layers,
    pollution_grades,
    read_pm25_station_data,
    render_pm25_map,
)


# 输出路径可按需要修改
output_folder = r'D:\PM2.5影响分析\不同等级污染日平均浓度分布图'


def calculate_level_daily_mean(station_frames):
    """按日均 PM2.5 浓度划分 Ⅰ-Ⅴ 级，计算各等级污染日的站点日均浓度均值。"""
    level_results = {grade_label: {} for grade_label, _, _, _ in pollution_grades}

    for station_name, frame in station_frames.items():
        daily_mean = get_daily_mean(frame)
        for grade_label, lower, upper, _ in pollution_grades:
            mask = get_grade_mask(daily_mean, lower, upper)
            value = daily_mean[mask].mean(skipna=True)
            if value == value:
                level_results[grade_label][station_name] = value

    return level_results


def main():
    print('正在读取并处理 PM2.5 数据...')
    station_frames = read_pm25_station_data()
    if not station_frames:
        raise RuntimeError('未读取到可用 PM2.5 数据，请检查 Excel 文件夹、sheet 名称和 00-23 小时列。')

    level_results = calculate_level_daily_mean(station_frames)
    base_layers = load_base_layers()

    for grade_label, _, _, range_label in pollution_grades:
        out_path = os.path.join(output_folder, f'PM25_{grade_label}级污染日平均浓度分布图_{range_label}.png')
        render_pm25_map(level_results[grade_label], base_layers, out_path)
        print(f'完成：{out_path}')


if __name__ == '__main__':
    main()

