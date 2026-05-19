import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import rioxarray
from rioxarray.merge import merge_arrays
import geopandas as gpd

# ==========================================
# 1. 核心路径与数据配置
# ==========================================
dem_folder = r'D:\Li-作图\dem' 
boundary_shapefile_path = r"D:\Li-作图\乌鲁木齐主城区边界\乌鲁木齐主城区\Urumqi_CityZone.shp"
excel_folder = r"D:\PM2.5影响分析\乌昌石数据总和" 
output_folder = r"D:\PM2.5影响分析\24小时浓度变化\Hourly_PM25_2"

os.makedirs(output_folder, exist_ok=True)

# 显示范围：乌鲁木齐局部
extent_small = [87.2, 87.9, 43.65, 44.25]

# 全局字体配置：20 号 Times New Roman 正体
global_font = {'family': 'Times New Roman', 'size': 20, 'weight': 'normal'}
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['axes.unicode_minus'] = False 

# ==========================================
# 2. 站点坐标映射 (简体中文严格对照)
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
    '府前路': ('FQL', 87.6403, 43.9685)
}

# ==========================================
# 3. 数据预处理
# ==========================================
print("正在读取并处理 PM2.5 数据...")
hourly_pm25_data = {f"{i:02d}": {} for i in range(24)}
cols_to_extract = [f"{i:02d}" for i in range(24)]
global_min_pm25, global_max_pm25 = float('inf'), float('-inf')

excel_files = glob.glob(os.path.join(excel_folder, "*.xlsx"))
for f in excel_files:
    filename = os.path.basename(f)
    station_name_cn = filename.split('_')[0].strip()
    
    matched_key = None
    for cn_key in cn_to_info.keys():
        if cn_key in station_name_cn or station_name_cn in cn_key:
            matched_key = cn_key
            break
            
    if matched_key is None: continue
        
    try:
        xl = pd.ExcelFile(f)
        target_sheet = next((s for s in xl.sheet_names if 'PM2.5' in s.upper() or 'PM25' in s.upper()), None)
        if target_sheet is None: continue
            
        df = xl.parse(target_sheet)
        df.columns = [str(col).zfill(2) if str(col).isdigit() else str(col) for col in df.columns]
        
        means = df[cols_to_extract].mean(skipna=True)
        for hour in cols_to_extract:
            if not np.isnan(means[hour]):
                val = means[hour]
                hourly_pm25_data[hour][matched_key] = val
                global_min_pm25 = min(global_min_pm25, val)
                global_max_pm25 = max(global_max_pm25, val)
    except: pass

if global_min_pm25 == float('inf'): global_min_pm25, global_max_pm25 = 0, 150

# ==========================================
# 4. 色带与分级配置
# ==========================================
dem_levels = [-100, 0, 250, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5100]
colors_15 = ["#2B4EA5", "#1D86E1", "#00ACC9", "#00C66B", "#61E24B", "#ADF26D", "#FFFF70", "#F6EA90", "#D9C673", "#B89963", "#9C7C5A", "#8B6D51", "#A99890", "#C9BCB6", "#E9E3E3"]
dem_cmap, dem_norm = mcolors.ListedColormap(colors_15), mcolors.BoundaryNorm(dem_levels, 15)

# PM2.5 5档不等距分级 
vmax_cbar = max(160, int(np.ceil(global_max_pm25))) 
pm25_levels = [0, 35, 75, 115, 150, vmax_cbar]

pm25_colors = ['#0000B2', '#A2A2FF', '#FFA3A3', '#FF0000', '#800000']
pm25_cmap = mcolors.ListedColormap(pm25_colors)
pm25_norm = mcolors.BoundaryNorm(pm25_levels, pm25_cmap.N)

# ==========================================
# 5. 绘图组件函数
# ==========================================
def add_vector_north_arrow(ax, x=0.04, y=0.92, w=0.015, h=0.05):
    ax.text(x, y + 0.005, 'N', ha='center', va='bottom', fontdict=global_font, transform=ax.transAxes, zorder=61)
    verts = [(x, y), (x - w, y - h), (x, y - h + h*0.25), (x + w, y - h)]
    ax.add_patch(mpatches.Polygon(verts, facecolor='black', edgecolor='black', transform=ax.transAxes, zorder=60))

def add_scale_bar(ax, x0, y0, length_km, y_offset):
    deg_len = length_km / (111.32 * np.cos(np.radians(y0)))
    ax.plot([x0, x0 + deg_len], [y0, y0], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0, x0], [y0, y0 + y_offset], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0 + deg_len/2, x0 + deg_len/2], [y0, y0 + y_offset*0.6], color='black', lw=1.2, transform=ccrs.PlateCarree(), zorder=60)
    ax.plot([x0 + deg_len, x0 + deg_len], [y0, y0 + y_offset], color='black', lw=1.5, transform=ccrs.PlateCarree(), zorder=60)
    ax.text(x0, y0 + y_offset*1.3, '0', ha='center', va='bottom', fontdict=global_font, transform=ccrs.PlateCarree(), zorder=60)
    ax.text(x0 + deg_len, y0 + y_offset*1.3, f'{length_km} km', ha='center', va='bottom', fontdict=global_font, transform=ccrs.PlateCarree(), zorder=60)

# ==========================================
# 6. 处理地形与边界
# ==========================================
print("正在处理边界与 DEM 数据...")
gdf_boundary = gpd.read_file(boundary_shapefile_path)
if gdf_boundary.crs and gdf_boundary.crs.to_epsg() != 4326: 
    gdf_boundary = gdf_boundary.to_crs(epsg=4326)

gdf_study_area = gdf_boundary.cx[extent_small[0]:extent_small[1], extent_small[2]:extent_small[3]]

datasets = []
for f in glob.glob(os.path.join(dem_folder, "*.tif")):
    try:
        ds = rioxarray.open_rasterio(f)
        ds = ds.rio.write_crs("EPSG:4326") if ds.rio.crs is None else ds.rio.reproject("EPSG:4326")
        datasets.append(ds.rio.clip_box(minx=extent_small[0]-0.05, miny=extent_small[2]-0.05, maxx=extent_small[1]+0.05, maxy=extent_small[3]+0.05))
    except: pass
merged_dem = merge_arrays(datasets).where(lambda x: x >= -500).sortby("y", ascending=False)
lon_dem, lat_dem, dem_val = merged_dem.x.values, merged_dem.y.values, merged_dem.values[0]

# ==========================================
# 7. 批量绘图 
# ==========================================
print("开始批量绘制 24 小时空间分布图...")
for hour in cols_to_extract:
    fig, ax = plt.subplots(figsize=(10, 9.5), subplot_kw={'projection': ccrs.PlateCarree()}, dpi=150)
    ax.set_extent(extent_small, crs=ccrs.PlateCarree())
    
    ax.pcolormesh(lon_dem, lat_dem, dem_val, cmap=dem_cmap, norm=dem_norm, transform=ccrs.PlateCarree(), shading='auto', rasterized=True, alpha=0.9)
    if not gdf_study_area.empty:
        ax.add_geometries(gdf_study_area.geometry, crs=ccrs.PlateCarree(), facecolor='none', edgecolor='black', linewidth=1.0, zorder=20, alpha=0.8)

    lons, lats, pm25_vals, abbr_names = [], [], [], []
    for cn_name, val in hourly_pm25_data[hour].items():
        abbr, lon, lat = cn_to_info[cn_name]
        if extent_small[0] < lon < extent_small[1] and extent_small[2] < lat < extent_small[3]:
            lons.append(lon); lats.append(lat); pm25_vals.append(val); abbr_names.append(abbr)

    if pm25_vals:
        ax.scatter(lons, lats, c=pm25_vals, cmap=pm25_cmap, norm=pm25_norm, s=150, edgecolor='white', linewidth=1.2, transform=ccrs.PlateCarree(), zorder=30)
        
        for x, y, name in zip(lons, lats, abbr_names):
            ax.text(x + 0.005, y + 0.005, name, fontdict=global_font, color='black', transform=ccrs.PlateCarree(), zorder=35)

    add_vector_north_arrow(ax)
    add_scale_bar(ax, x0=87.73, y0=43.68, length_km=10, y_offset=0.015)
    
    gl = ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5, color='gray')
    gl.top_labels = gl.right_labels = False
    gl.xformatter, gl.yformatter = LongitudeFormatter(number_format='.1f'), LatitudeFormatter(number_format='.1f')
    gl.xlocator, gl.ylocator = mticker.MultipleLocator(0.2), mticker.MultipleLocator(0.1)
    gl.xlabel_style = gl.ylabel_style = global_font
    
    # 缩小 bottom 参数，让主图向下延展，拉近与图例的距离
    plt.subplots_adjust(left=0.1, bottom=0.18, right=0.95, top=0.95)

    # 提高图例的起始 y 坐标 (提升至 0.10)，消除多余空白
    cbar_ax = fig.add_axes([0.2, 0.10, 0.6, 0.025])
    sm = plt.cm.ScalarMappable(cmap=pm25_cmap, norm=pm25_norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal', ticks=pm25_levels)
    
    cbar.set_label('PM2.5 concentrations (μg·m⁻³)', fontdict=global_font, labelpad=8)
    cbar.ax.tick_params(labelsize=20)
    cbar.ax.set_xticklabels([f"{val}" for val in pm25_levels])

    out_path = os.path.join(output_folder, f"{hour}.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig) 

print(f"\n✅ 布局已调整完毕！已全部替换为简体中文。")