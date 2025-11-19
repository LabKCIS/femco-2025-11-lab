import json
import boto3
import pandas as pd
import pymysql
import os
import io
import re
from botocore.exceptions import ClientError

# --- Configuration ---
s3_client = boto3.client('s3')

# DB Settings from Environment Variables
RDS_HOST = os.environ.get('RDS_HOST')
RDS_USER = os.environ.get('RDS_USER')
RDS_PASSWORD = os.environ.get('RDS_PASSWORD')
RDS_DB_NAME = os.environ.get('RDS_DB_NAME')

def get_db_connection():
    """建立 RDS 連線"""
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except pymysql.MySQLError as e:
        print(f"ERROR: Could not connect to MySQL instance. {e}")
        raise e

def clean_key(text):
    """將 lookup key 正規化，移除所有空白、全形空白和括號。"""
    if pd.isna(text) or text is None:
        return ""
    # 移除所有空白、全形空白、換行符、和括號
    text = re.sub(r'[\s　\n\r\(\)]', '', str(text))
    return text.strip()

def get_val(df, row_idx, col_idx):
    """安全地從 DataFrame 提取值，並返回 None 如果值為空或 NaN。"""
    try:
        val = df.iloc[row_idx, col_idx]
        # 使用 str(val).strip() 檢查空值，包括只有空白字符的情況
        if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
            return None
        return str(val).strip()
    except IndexError:
        return None

def find_idx(df, row_map, keyword):
    """在動態地圖中尋找關鍵字對應的 Row Index。"""
    clean_key_name = clean_key(keyword)
    if clean_key_name in row_map:
        return row_map[clean_key_name]
    return None

def parse_csv(content, filename):
    """
    解析非結構化 CSV 內容，並只為 InspectionTimePoint 有文字值的欄位生成紀錄。
    """
    df = pd.read_csv(io.StringIO(content), header=None)
    
    # 建立 "Cleaned Key" -> "Row Index" 的動態地圖
    row_map = {}
    for idx, row in df.iterrows():
        k0 = clean_key(row[0])
        if k0: row_map[k0] = idx
        if len(row) > 1:
            k1 = clean_key(row[1])
            if k1 and k1 not in row_map:
                row_map[k1] = idx

    # --- 1. 提取靜態/Header 資訊 ---
    header_info = {'filename': filename}
    # 提取所有 Header 邏輯... (略，與前版相同)
    r = find_idx(df, row_map, "工令單號碼")
    if r is not None:
        header_info['WorkOrderNo'] = get_val(df, r, 1)
        row_vals = df.iloc[r].astype(str).tolist()
        for i, cell in enumerate(row_vals):
            if "客戶" in cell:
                header_info['Customer'] = get_val(df, r, i+1)
                break
    
    r = find_idx(df, row_map, "鋼管規格")
    if r is not None:
        header_info['Specification'] = get_val(df, r, 1)
        row_vals = df.iloc[r].astype(str).tolist()
        for i, cell in enumerate(row_vals):
            if "材質" in cell:
                header_info['Material'] = get_val(df, r, i+1)
                break
    
    r = find_idx(df, row_map, "品保課長")
    if r is not None:
        header_info['QA_Manager'] = get_val(df, r, 1)
        header_info['Production_Manager'] = get_val(df, r, 3) 
        header_info['Inspector'] = get_val(df, r, 5)

    r = find_idx(df, row_map, "判定")
    if r is not None:
        header_info['Judgement'] = get_val(df, r, 2)
    
    # --- 2. 確定所有量測欄位及其 Row Index ---
    measurement_fields = {
        "StripWidth": "鋼帶寬度", "StripThickness": "鋼帶厚度", "Current": "電流", 
        "Voltage": "電壓", "WeldingSpeed": "熔接速度", "AnnealingTemp": "焊縫退火溫度",
        "WeldSeam": "内外焊道刮除", "WeldSeamAppearance": "外焊道需平順", "Sizing_Da": "定徑前(Da)", 
        "Sizing_Db": "定徑後(Db)", "SizingRate": "定徑率", "OD_Upper": "外徑", 
        "OD_Lower": "下限", "Roundness": "真圓度", "Appearance": "外觀", 
        "Length": "長度", "Straightness": "直度", "PortVerticality": "端口垂直度", 
        "BevelAngle": "修端斜角", "RootFace": "根面", "BendFlattening": "導彎、壓扁"
    }
    measurement_row_map = {}
    for db_col, csv_key in measurement_fields.items():
        measurement_row_map[db_col] = find_idx(df, row_map, csv_key)

    # --- 3. 識別並過濾時間點欄位 (Time Point Columns) ---
    valid_time_points = []
    r_time = find_idx(df, row_map, "檢驗項目")
    
    # 嚴格判斷 '時間標準' 的清理後名稱
    clean_time_standard = clean_key("時間標準")
    
    if r_time is not None:
        time_points_row = df.iloc[r_time, 2:].tolist()
        start_col_idx = 2
        
        for i, label in enumerate(time_points_row):
            
            # **核心過濾邏輯**
            # 1. 確保 label 不是 None
            # 2. 確保 label 移除空白後不為空字串 (這是只保留有填文字紀錄的關鍵)
            # 3. 確保 label 清理後不等於 "時間標準"
            cleaned_label = clean_key(label)
            
            if label is not None and cleaned_label != '' and cleaned_label != clean_time_standard:
                valid_time_points.append({
                    'label': cleaned_label, 
                    'col_idx': start_col_idx + i
                })

    # --- 4. 按有效時間點欄位迭代，創建紀錄 ---
    all_records = []
    
    for tp in valid_time_points:
        record = header_info.copy()
        record['InspectionTimePoint'] = tp['label'] 
        current_col_idx = tp['col_idx']
        
        has_measurement_data = False
        
        # 迭代量測欄位
        for db_col, row_idx in measurement_row_map.items():
            if row_idx is not None:
                measured_val = get_val(df, row_idx, current_col_idx)
                
                # 只有當量測值不為 None 時才將其加入字典
                if measured_val is not None:
                    record[db_col] = measured_val
                    has_measurement_data = True

        # 只有當紀錄中包含至少一個量測值時才保留這條紀錄
        if has_measurement_data:
             all_records.append(record)

    return all_records

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read().decode('utf-8', errors='ignore')
        
        records = parse_csv(content, key)
        print(f"Parsed {len(records)} records from file: {key}")
        
        if not records:
            print("No valid inspection records found with measurable data. Exiting.")
            return {"statusCode": 200, "body": f"No measurable records found in {key}"}

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 取得所有欄位名稱 (基於所有紀錄中出現的唯一欄位)
            all_columns = set()
            for record in records:
                all_columns.update(record.keys())
            
            columns_to_insert = sorted(list(all_columns))

            # 準備批量插入的值
            values_to_insert = []
            for record in records:
                values_to_insert.append(tuple(record.get(col, None) for col in columns_to_insert))
            
            placeholders = ', '.join(['%s'] * len(columns_to_insert))
            col_names = ', '.join(columns_to_insert)
            
            sql = f"INSERT INTO inspection_records ({col_names}) VALUES ({placeholders})"
            
            # 執行批量插入
            cursor.executemany(sql, values_to_insert)
            conn.commit()
            
        return {"statusCode": 200, "body": f"Successfully inserted {len(records)} records from {key}"}

    except Exception as e:
        print(f"Error processing {key}: {str(e)}")
        if 'RDS_HOST' not in os.environ or not RDS_HOST:
             print("Please ensure RDS_HOST, RDS_USER, RDS_PASSWORD, and RDS_DB_NAME environment variables are set.")
        return {"statusCode": 500, "body": str(e)}
