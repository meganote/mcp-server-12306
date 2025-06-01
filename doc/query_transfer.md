# query_transfer 工具文档

## 功能说明
官方 12306 一次中转换乘方案查询。输入出发站、到达站、日期，返回一次换乘的最优方案，含所有中转车次、时刻、余票、历时等详细信息。

## 实现方法
- 调用 12306 官网中转方案接口，支持 middle_station、isShowWZ、purpose_codes 等参数。
- 自动分页抓取全部中转方案，输出每段车次、时刻、余票、等候时间、总历时等。
- 结果结构与 12306 官网一致，支持 MCP 协议封装。

## 使用方法
### 请求参数
- from_station: 出发站
- to_station: 到达站
- train_date: 出发日期（YYYY-MM-DD）
- middle_station: 中转站（可选）
- isShowWZ: 是否显示无座车次（Y/N，可选）
- purpose_codes: 乘客类型（如“ADULT”，可选）

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
  "transfers": [
    {
      "segments": [
        { "train_no": "G1234", ... },
        { "train_no": "G5678", ... }
      ],
      "wait_time": "00:30",
      "total_duration": "02:10"
    }
  ]
}
```
