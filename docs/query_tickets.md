# query_tickets 工具文档

## 功能说明
官方 12306 余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。

## 实现方法
- 调用 12306 官网余票查询接口，解析返回的车次、时刻、历时、各席别余票等字段。
- 支持参数校验、车站名/三字码自动转换。
- 返回结构与 12306 官网一致，支持 MCP 协议封装。

## 使用方法
### 请求参数
- from_station: 出发站（如“九江”或“JJG”）
- to_station: 到达站（如“永修”或“三字码”）
- train_date: 出发日期（YYYY-MM-DD）
- purpose_codes: 乘客类型（如“ADULT”）

### 示例
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01"
}
```

### 返回示例
```json
{
  "tickets": [
    {
      "train_no": "G1234",
      "from_station_name": "九江",
      "to_station_name": "永修",
      "start_time": "08:00",
      "arrive_time": "08:26",
      "duration": "00:26",
      "can_web_buy": "Y",
      "business_seat_num": "有",
      "first_class_num": "有",
      "second_class_num": "有",
      ...
    }
  ],
  "total": 20
}
```
