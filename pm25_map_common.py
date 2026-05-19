# -*- coding: utf-8 -*-
import glob
import os

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import rioxarray
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
import cartopy.crs as ccrs
from rioxarray.merge import merge_arrays


# ==========================================
# 1. 核心路径与数据配置
# ==========================================
dem_folder = r'D:\Li-作图\dem'
boundary_shapefile_path = r'D:\Li-作图\乌鲁木齐主城区边界\乌鲁木齐主城区\Urumqi_CityZone.shp'
excel_folder = r'D:\PM2.5影响分析\乌昌石数据总和'

# 显示范围：乌鲁木齐局部，保持原代码经纬度范围不变
extent_small = [87.2, 87.9, 43.65, 44.25]

# 全局字体配置：保持原代码样式
global_font = {'family': 'Times New Roman', 'size': 20, 'weight': 'normal'}
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 2. 站点坐标映射：保持原代码缩写和经纬度不变
# ==========================================
cn_to_info = {
    '石河子艾青诗歌馆': ('AQ', 86.0417, 44.2992),
    '南区管委会': ('NQ', 86.0502, 44.2383),
    '世纪广场': ('SJ', 86.08213, 44.30306),
    '农水大厦': ('NSDS', 87.53828, 44.16169),
    '经开区管委会': ('JKQ', 87.54904, 44.19197),
    '新区政务中心': ('XQZW', 87.2717, 44.0297),
    '亚心广场': ('YXGC', 87.3095, 44.0142),
    '收费所': ('SFS', 87.6046, 43.7680),
    '监测站': ('JCZ', 87.5801, 43.8303),
    '铁路局': ('TLJ', 87.5525, 43.8711),
    '三十一中学': ('31Z', 87.6432, 43.8310),
    '米东区环保局': ('MD', 87.7216, 44.1747),
    '培训基地': ('PX', 87.4651, 43.4569),
    '达坂城区环保局': ('DB', 88.3118, 43.3658),
    '红光山片区': ('HGS', 87.6162, 43.8801),
    '新师大温泉校区': ('XSD', 87.7024, 43.8004),
    '大绿谷': ('DLG', 87.4921, 43.8411),
    '新疆农科院农场': ('NKY', 87.4754, 43.9469),
    '大湾': ('DW', 87.6491, 43.7694),
    '北京北路': ('BJBL', 87.5426, 43.9158),
    '白鸟湖': ('BNH', 87.4255, 43.8248),
    '西山雅山新天地': ('YS', 87.5358, 43.7987),
    '七十四中学': ('74Z', 87.4190, 43.8724),
    '府前路': ('FQL', 87.6403, 43.9685),
}

hour_cols = [f'{i:02d}' for i in range(24)]

# PM2.5 浓度分级：[0,35]，（35,75]，（75,115]，（115,150]，（150,无穷]
pollution_grades = [
    ('Ⅰ', 0, 35, '[0,35]'),
    ('Ⅱ', 35, 75, '(35,75]'),
    ('Ⅲ', 75, 115, '(75,115]'),
    ('Ⅳ', 115, 150, '(115,150]'),
    ('Ⅴ', 150, np.inf, '(150,∞]'),
]

# DEM 分级与配色：保持原代码间隔和颜色不变
dem_levels = [-100, 0, 250, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5100]
colors_15 = [
    '#2B4EA5', '#1D86E1', '#00ACC9', '#00C66B', '#61E24B',
    '#ADF26D', '#FFFF70', '#F6EA90', '#D9C673', '#B89963',
    '#9C7C5A', '#8B6D51', '#A99890', '#C9BCB6', '#E9E3E3',
]
dem_cmap = mcolors.ListedColormap(colors_15)
dem_norm = mcolors.BoundaryNorm(dem_levels, 15)

pm25_colors = ['#0000B2', '#A2A2FF', '#FFA3A3', '#FF0000', '#800000']
pm25_cmap = mcolors.ListedColormap(pm25_colors)


def normalize_column_name(col):
    raw = str(col).strip()
    try:
        value = float(raw)
        if value.is_integer() and 0 <= int(value) <= 23:
            return f'{int(value):02d}'
    except ValueError:
        pass
    return raw.zfill(2) if raw.isdigit() else raw


def match_station_name(filename):
    station_name_cn = os.path.basename(filename).split('_')[0].strip()
    for cn_key in cn_to_info.keys():
        if cn_key in station_name_cn or station_name_cn in cn_key:
            return cn_key
    return None


def read_pm25_station_data(folder=excel_folder):
    """读取原始 Excel 格式，返回 {中文站点名: 24小时浓度DataFrame}。"""
    station_frames = {}

    for path in glob.glob(os.path.join(folder, '*.xlsx')):
        station_name = match_station_name(path)
        if station_name is None:
            continue

        try:
            xl = pd.ExcelFile(path)
            target_sheet = next((s for s in xl.sheet_names if 'PM2.5' in s.upper() or 'PM25' in s.upper()), None)
            if target_sheet is None:
                continue

            df = xl.parse(target_sheet)
            df.columns = [normalize_column_name(col) for col in df.columns]
            missing_cols = [col for col in hour_cols if col not in df.columns]
            if missing_cols:
                print(f'跳过 {os.path.basename(path)}：缺少小时列 {missing_cols}')
                continue

            values = df[hour_cols].apply(pd.to_numeric, errors='coerce')
            values = values.dropna(how='all')
            if values.empty:
                continue

            if station_name in station_frames:
                station_frames[station_name] = pd.concat([station_frames[station_name], values], ignore_index=True)
            else:
                station_frames[station_name] = values.reset_index(drop=True)
        except Exception as exc:
            print(f'跳过 {os.path.basename(path)}：{exc}')

    return station_frames


def get_daily_mean(frame):
    return frame[hour_cols].mean(axis=1, skipna=True)


def get_grade_mask(daily_mean, lower, upper):
    if np.isinf(upper):
        return daily_mean > lower
    if lower == 0:
        return (daily_mean >= lower) & (daily_mean <= upper)
    return (daily_mean > lower) & (daily_mean <= upper)


def get_pm25_norm(values_by_station):
    valid_values = [float(v) for v in values_by_station.values() if pd.notna(v)]
    max_value = max(valid_values) if valid_values else 150
    vmax_cbar = max(160, int(np.ceil(max_value)))
    pm25_levels = [0, 35, 75, 115, 150, vmax_cbar]
    pm25_norm = mcolors.BoundaryNorm(pm25_levels, pm25_cmap.N, clip=True)
    return pm25_norm, pm25_levels


def load_base_layers():
    print('正在处理边界与 DEM 数据...')
    gdf_boundary = gpd.read_file(boundary_shapefile_path)
    if gdf_boundary.crs and gdf_boundary.crs.to_epsg() != 4326:
        gdf_boundary = gdf_boundary.to_crs(epsg=4326)
    gdf_study_area = gdf_boundary.cx[extent_small[0]:extent_small[1], extent_small[2]:extent_small[3]]

    datasets = []
    for path in glob.glob(os.path.join(dem_folder, '*.tif')):
        try:
            ds = rioxarray.open_rasterio(path)
            ds = ds.rio.write_crs('EPSG:4326') if ds.rio.crs is None else ds.rio.reproject('EPSG:4326')
            ds = ds.rio.clip_box(
                minx=extent_small[0] - 0.05,
                miny=extent_small[2] - 0.05,
                maxx=extent_small[1] + 0.05,
                maxy=extent_small[3] + 0.05,
            )
            datasets.append(ds)
        except Exception as exc:
            print(f'跳过 DEM {os.path.basename(path)}：{exc}')

    if not datasets:
        raise RuntimeError(f'未在 DEM 文件夹中读取到可用 tif：{dem_folder}')

    merged_dem = merge_arrays(datasets).where(lambda x: x >= -500).sortby('y', ascending=False)
    return {
        'gdf_study_area': gdf_study_area,
        'lon_dem': merged_dem.x.values,
        'lat_dem': merged_dem.y.values,
        'dem_val': merged_dem.values[0],
    }


def add_vector_north_arrow(ax, x=0.04, y=0.92, w=0.015, h=0.05):
    ax.text(x, y + 0.005, 'N', ha='center', va='bottom', fontdict=global_font, transform=ax.transAxes, zorder=61)
    verts = [(x, y), (x - w, y - h), (x, y - h + h * 0.25), (x + w, y - h)]
    ax.add_patch(mpatches.Polygon(verts, facecolor='black', edgecolor='black', transform=ax.transAxes, zorder=60))


def add_scale_bar(ax, x0, y0, length_km, y_offset):
    deg_len = length_km / (111.32 * np.cos(np.radians(y0)))
    ax.plot([x0, x0 + deg_len], [y0, y0], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0, x0], [y0, y0 + y_offset], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0 + deg_len / 2, x0 + deg_len / 2], [y0, y0 + y_offset * 0.6], color='black', lw=1.2, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0 + deg_len, x0 + deg_len], [y0, y0 + y_offset], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.text(x0, y0 + y_offset * 1.3, '0', ha='center', va='bottom', fontdict=global_font, transform=ccrs.PlateCarree(), zorder=60)
    ax.text(x0 + deg_len, y0 + y_offset * 1.3, f'{length_km} km', ha='center', va='bottom', fontdict=global_font, transform=ccrs.PlateCarree(), zorder=60)


def render_pm25_map(values_by_station, base_layers, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 9.5), subplot_kw={'projection': ccrs.PlateCarree()}, dpi=150)
    ax.set_extent(extent_small, crs=ccrs.PlateCarree())

    ax.pcolormesh(
        base_layers['lon_dem'],
        base_layers['lat_dem'],
        base_layers['dem_val'],
        cmap=dem_cmap,
        norm=dem_norm,
        transform=ccrs.PlateCarree(),
        shading='auto',
        rasterized=True,
        alpha=0.9,
    )

    gdf_study_area = base_layers['gdf_study_area']
    if not gdf_study_area.empty:
        ax.add_geometries(
            gdf_study_area.geometry,
            crs=ccrs.PlateCarree(),
            facecolor='none',
            edgecolor='black',
            linewidth=1.0,
            zorder=20,
            alpha=0.8,
        )

    lons, lats, pm25_vals, abbr_names = [], [], [], []
    for cn_name, val in values_by_station.items():
        if cn_name not in cn_to_info or pd.isna(val):
            continue
        abbr, lon, lat = cn_to_info[cn_name]
        if extent_small[0] < lon < extent_small[1] and extent_small[2] < lat < extent_small[3]:
            lons.append(lon)
            lats.append(lat)
            pm25_vals.append(float(val))
            abbr_names.append(abbr)

    pm25_norm, pm25_levels = get_pm25_norm(values_by_station)

    if pm25_vals:
        ax.scatter(
            lons,
            lats,
            c=pm25_vals,
            cmap=pm25_cmap,
            norm=pm25_norm,
            s=150,
            edgecolor='white',
            linewidth=1.2,
            transform=ccrs.PlateCarree(),
            zorder=30,
        )

        for x, y, name in zip(lons, lats, abbr_names):
            ax.text(x + 0.005, y + 0.005, name, fontdict=global_font, color='black', transform=ccrs.PlateCarree(), zorder=35)

    add_vector_north_arrow(ax)
    add_scale_bar(ax, x0=87.73, y0=43.68, length_km=10, y_offset=0.015)

    gl = ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5, color='gray')
    gl.top_labels = gl.right_labels = False
    gl.xformatter = LongitudeFormatter(number_format='.1f')
    gl.yformatter = LatitudeFormatter(number_format='.1f')
    gl.xlocator = mticker.MultipleLocator(0.2)
    gl.ylocator = mticker.MultipleLocator(0.1)
    gl.xlabel_style = gl.ylabel_style = global_font

    plt.subplots_adjust(left=0.1, bottom=0.18, right=0.95, top=0.95)

    cbar_ax = fig.add_axes([0.2, 0.10, 0.6, 0.025])
    sm = plt.cm.ScalarMappable(cmap=pm25_cmap, norm=pm25_norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal', ticks=pm25_levels)
    cbar.set_label('PM2.5 concentrations (μg·m⁻³)', fontdict=global_font, labelpad=8)
    cbar.ax.tick_params(labelsize=20)
    cbar.ax.set_xticklabels(['0', '35', '75', '115', '150', '>150'])

    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
