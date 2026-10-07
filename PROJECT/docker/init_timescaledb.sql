-- ========================================================
-- TimescaleDB 初始化腳本 (Tesla Powerwall EMS)
-- ========================================================

-- 1. 啟用 TimescaleDB 擴充功能
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. 案場中繼資料表 (Sites Metadata)
CREATE TABLE IF NOT EXISTS sites (
    site_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    teg_ip VARCHAR(64) DEFAULT '192.168.1.100',
    battery_capacity_kwh DOUBLE PRECISION DEFAULT 13.5,
    max_solar_kw DOUBLE PRECISION DEFAULT 10.0,
    timezone VARCHAR(64) DEFAULT 'Asia/Taipei',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 預設預載案場 A 與案場 B (對應架構圖)
INSERT INTO sites (site_id, name, teg_ip, battery_capacity_kwh, max_solar_kw)
VALUES 
    ('site_01', '案場 A (Site 1 - 台北示範案場)', '192.168.1.101', 13.5, 10.0),
    ('site_02', '案場 B (Site 2 - 新竹儲能案場)', '192.168.1.102', 27.0, 20.0)
ON CONFLICT (site_id) DO NOTHING;

-- 3. 遙測時間序列資料表 (Telemetry Hypertable)
CREATE TABLE IF NOT EXISTS telemetry_records (
    time TIMESTAMPTZ NOT NULL,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    solar_kw DOUBLE PRECISION DEFAULT 0.0,
    grid_kw DOUBLE PRECISION DEFAULT 0.0,
    battery_kw DOUBLE PRECISION DEFAULT 0.0,
    home_kw DOUBLE PRECISION DEFAULT 0.0,
    soc_pct DOUBLE PRECISION DEFAULT 0.0,
    grid_status VARCHAR(32) DEFAULT 'Connected',
    raw_payload JSONB DEFAULT '{}'::jsonb
);

-- 將一般 PostgreSQL 表轉換為 TimescaleDB Hypertable (自動以 7 天作為 chunk 分區)
SELECT create_hypertable('telemetry_records', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

-- 建立索引加速多維度時序查詢
CREATE INDEX IF NOT EXISTS idx_telemetry_site_time ON telemetry_records (site_id, time DESC);

-- 4. 啟用自動資料壓縮策略 (超過 30 天的資料自動以行式壓縮存儲，節省 90% 硬碟空間)
ALTER TABLE telemetry_records SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'site_id',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('telemetry_records', INTERVAL '30 days', if_not_exists => TRUE);

-- 5. 建立小時級連續聚合檢視表 (Continuous Aggregates for Fast Dashboard Trends)
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly_summary
WITH (timescaledb.continuous) AS
SELECT 
    site_id,
    time_bucket('1 hour', time) AS bucket,
    AVG(solar_kw) AS avg_solar_kw,
    MAX(solar_kw) AS peak_solar_kw,
    AVG(grid_kw) AS avg_grid_kw,
    AVG(battery_kw) AS avg_battery_kw,
    AVG(home_kw) AS avg_home_kw,
    LAST(soc_pct, time) AS end_soc_pct
FROM telemetry_records
GROUP BY site_id, bucket
WITH NO DATA;

-- 自動刷新連續聚合策略 (每 30 分鐘自動計算過去 2 小時數據)
SELECT add_continuous_aggregate_policy('telemetry_hourly_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);

-- 6. 遠端控制稽核紀錄表 (Tesla Fleet API Control Logs)
CREATE TABLE IF NOT EXISTS control_logs (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    command_type VARCHAR(64) NOT NULL, -- 'backup_reserve', 'operation_mode'
    parameters JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING', -- 'PENDING', 'SENT', 'SUCCESS', 'FAILED'
    tesla_command_id VARCHAR(128),
    tesla_response JSONB DEFAULT '{}'::jsonb,
    error_message TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_control_logs_site ON control_logs (site_id, created_at DESC);
