資料表: inspection\_records 欄位對照表

| 類別  | 中文欄位名稱 (CSV 關鍵字) | 英文欄位名稱 (DB Column) | 備註 (數據來源) |
| --- | --- | --- | --- |
| **系統** | 檔案名稱 | `filename` | 來源檔案名 |
|     | 紀錄 ID | `id` | 主鍵，自動生成 |
|     | 建立時間 | `created_at` | 數據寫入時間 |
| **時間點** | 檢驗項目/時間標籤 | `InspectionTimePoint` | **必須有值** 的欄位 (e.g., `0814`, `0903`) |
| **報表頭** | 工令單號碼 | `WorkOrderNo` |     |
|     | 客戶  | `Customer` |     |
|     | 鋼管規格 | `Specification` |     |
|     | 材質  | `Material` |     |
| **量測值** | 鋼帶寬度 | `StripWidth` |     |
|     | 鋼帶厚度 | `StripThickness` |     |
|     | 電流  | `Current` |     |
|     | 電壓  | `Voltage` |     |
|     | 熔接速度 | `WeldingSpeed` |     |
|     | 焊縫退火溫度 | `AnnealingTemp` |     |
|     | 内外焊道刮除 | `WeldSeam` |     |
|     | 外焊道需平順 | `WeldSeamAppearance` |     |
|     | 定徑前(Da) | `Sizing_Da` |     |
|     | 定徑後(Db) | `Sizing_Db` |     |
|     | 定徑率(Da-Db)/Da | `SizingRate` |     |
|     | 外徑 (上限) | `OD_Upper` |     |
|     | 下限 (外徑下限) | `OD_Lower` |     |
|     | 真圓度 | `Roundness` |     |
|     | 外觀  | `Appearance` |     |
|     | 長度  | `Length` |     |
|     | 直度  | `Straightness` |     |
|     | 端口垂直度 | `PortVerticality` |     |
|     | 修端斜角 | `BevelAngle` |     |
|     | 根面  | `RootFace` |     |
|     | 導彎、壓扁 | `BendFlattening` |     |
| **簽核/結論** | 判定  | `Judgement` |     |
|     | 品保課長 | `QA_Manager` |     |
|     | 製管課長 | `Production_Manager` |     |
|     | 檢查員 | `Inspector` |
