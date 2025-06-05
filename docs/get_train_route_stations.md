# get_train_route_stations 工具文档

## 功能说明
查询指定列车的经停站信息。输入车次号、出发站、到达站、日期，返回该车次所有经停站、到发时刻、停留时间等详细信息。

## 实现方法
- 调用 12306 官网经停站接口，支持车次号或官方编号自动转换。
- 返回所有经停站、到发时刻、停留时间，结构与 12306 官网一致。

## 使用方法
### 请求参数
- from_station: 出发站
- to_station: 到达站
- train_date: 出发日期（YYYY-MM-DD）
- train_no: 车次号（如“G1234”）

### 示例
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01",
  "train_no": "G1234"
}
```

### 返回示例
```json
{
  "route": [
    {
      "station_name": "九江",
      "arrive_time": "--",
      "start_time": "08:00",
      "stopover_time": "--"
    },
    {
      "station_name": "永修",
      "arrive_time": "08:26",
      "start_time": "--",
      "stopover_time": "2分"
    }
  ]
}
```
