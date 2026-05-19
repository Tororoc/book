# -*- coding: utf-8 -*-
import os

from pm25_map_common import (
    get_daily_mean,
    get_grade_mask,
    hour_cols,
    load_base_layers,
    pollution_grades,
    read_pm25_station_data,
    render_pm25_map,
)


# 输出路径可按需要修改
output_folder = r'D:\PM2.5影响分析\不同等级污染日逐小时平均浓度分布图'


def calculate_level_hourly_mean(station_frames):
    """按日均 PM2.5 浓度划分 Ⅰ-Ⅴ 级，计算各等级污染日每小时的站点平均浓度。"""
    level_hourly_results = {
        grade_label: {hour: {} for hour in hour_cols}
        for grade_label, _, _, _ in pollution_grades
    }

    for station_name, frame in station_frames.items():
        daily_mean = get_daily_mean(frame)
        for grade_label, lower, upper, _ in pollution_grades:
            mask = get_grade_mask(daily_mean, lower, upper)
            if not mask.any():
                continue

            selected = frame.loc[mask, hour_cols]
            hourly_mean = selected.mean(axis=0, skipna=True)
            for hour in hour_cols:
                value = hourly_mean[hour]
                if value == value:
                    level_hourly_results[grade_label][hour][station_name] = value

    return level_hourly_results


def main():
    print('正在读取并处理 PM2.5 数据...')
    station_frames = read_pm25_station_data()
    if not station_frames:
        raise RuntimeError('未读取到可用 PM2.5 数据，请检查 Excel 文件夹、sheet 名称和 00-23 小时列。')

    level_hourly_results = calculate_level_hourly_mean(station_frames)
    base_layers = load_base_layers()

    for grade_label, _, _, range_label in pollution_grades:
        grade_folder = os.path.join(output_folder, f'{grade_label}级_{range_label}')
        for hour in hour_cols:
            out_path = os.path.join(grade_folder, f'PM25_{grade_label}级污染日_{hour}时平均浓度分布图.png')
            render_pm25_map(level_hourly_results[grade_label][hour], base_layers, out_path)
            print(f'完成：{out_path}')


if __name__ == '__main__':
    main()

