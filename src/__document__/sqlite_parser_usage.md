# SQLite 解析类 (SQLiteParser) 使用文档

## 目录
1. [类概述](#类概述)
2. [初始化配置](#初始化配置)
3. [表操作](#表操作)
   - [3.1 创建表](#31-创建表)
4. [数据操作](#数据操作)
   - [4.1 插入数据](#41-插入数据)
5. [查询语法](#查询语法)
   - [注意事项](#注意事项)
7. [完整示例](#完整示例)

---

## 类概述
`SQLiteParser` 是一个面向 SQLite 数据库的高级 DSL 解析器，提供以下核心功能：
- 自动化表结构管理
- 类型安全的批量数据插入
- 自定义查询语法解析
- 数据库连接池管理
- 自动事务处理

---

## 初始化配置
```python
from sqlite_client import SQLiteClient
from sqlite_parser import SQLiteParser

# 1. 创建客户端
client = SQLiteClient('mydb.db', pool_size=5)

# 2. 初始化解析器 (需指定默认表)
parser = SQLiteParser(client, default_table='users')
```

## 表操作

### 3.1 创建表

**方法签名**:

```python
create_table(table_name: str, columns: List[Dict[str, Any]]) -> None
```

**参数说明**：

| 参数名     | 类型       | 说明                          |
| :--------- | :--------- | :---------------------------- |
| table_name | str        | 要创建的表名                  |
| columns    | List[Dict] | 列定义列表，每个字典包含：    |
|            |            | - name: 列名 (str)            |
|            |            | - type: 数据类型 (Python类型) |
|            |            | - primary: 是否主键 (bool)    |
|            |            | - unique: 是否唯一 (bool)     |

**标量类型映射**：

| Python 类型 | SQLite 类型 |
| :---------- | :---------- |
| str         | TEXT        |
| int         | INTEGER     |
| float       | REAL        |
| bytes       | BLOB        |
| bool        | INTEGER     |

**示例**：

```python
# 创建用户表
parser.create_table('users', [
    {"name": "id", "type": int, "primary": True},
    {"name": "name", "type": str, "unique": True},
    {"name": "age", "type": int},
    {"name": "vip", "type": bool}
])
```

------

## 数据操作

### 4.1 插入数据

**方法签名**:

```python
insert(data: Union[List, Dict, List[Union[List, Dict]]], 
       table_name: Optional[str] = None) -> List[Optional[int]]
```

**支持格式**：

```python
# 字典格式 (自动按列名匹配)
{"id": 1, "name": "Alice", "age": 25}

# 列表格式 (按列顺序)
[2, "Bob", 30]

# 批量插入
[
    {"id": 3, "name": "Charlie"},
    [4, "David", 28],
    (5, "Eva", 35)  # 元组格式
]
```

**返回值**：

- 返回插入成功的行ID列表

**示例**：

```python
# 单条插入
parser.insert({"id": 1, "name": "Alice", "age": 25})

# 批量插入
parser.insert([
    [2, "Bob", 30],
    {"id": 3, "name": "Charlie", "age": 28}
])
```

------

## 查询语法

### 5.1 基础查询

**语法结构**：

```
\select [条件组] [\columns 列名列表] [\from 表名] \select

\select [QUERY_CONDITIONS] [\columns COLUMN_LIST] [\from TABLE_NAME] \select
```

**示例**：

```python
# 查询ID=1或3的记录
results = parser.select(r"\select 1 | 3 \select")

# 等效SQL
SELECT * FROM users WHERE id IN (1, 3)
```

### 5.2. 组件说明

| 组件               | 说明                                   |
| :----------------- | :------------------------------------- |
| `\select`          | 查询开始/结束标记（必须成对出现）      |
| `QUERY_CONDITIONS` | 主键查询条件组，使用逗号分隔多个条件组 |
| `\columns`         | 指定返回列（可选），未指定时返回所有列 |
| `COLUMN_LIST`      | 逗号分隔的列名列表                     |
| `\from`            | 指定查询表（可选），未指定时使用默认表 |

### 5.3 条件组运算符说明

| 运算符 | 名称 | 行为                                         |
| :----- | :--- | :------------------------------------------- |
| `|`    | 或   | 从左到右短路匹配，找到第一个存在的记录后停止 |
| `,`    | 并   | 执行多个独立查询，结果合并返回               |

**复杂示例**：

```python
# 查询顺序：
# 1. 先找ID=1的记录，存在则返回
# 2. 查找ID=5的记录，无论是否找到都继续
# 3. 最后查找ID=3的记录
parser.select(r"\select 1 | 5, 3 \from users \select")

# 可能结果：
[
    {'id':1, 'name':'Alice'},  # 来自第一个条件组
    {'id':3, 'name':'Charlie'} # 来自第二个条件组
]
```

### 5.4 条件组特殊语法

#### 模糊查询

- 在条件值后添加 `?` 后缀触发模糊查询
- 自动转换为 SQL `LIKE` 语句
- 支持标准通配符：`%` (任意字符) 和 `_` (单个字符)

**示例：**

```
user123?      =>  WHERE primary_key LIKE 'user123%'
john@domain?  =>  WHERE email LIKE 'john@domain%'
2023-%-01?    =>  WHERE date LIKE '2023-%-01%'
```

#### 多条件组

- 使用 `,` 分隔多个条件组
- 每个条件组使用 `|` 分隔多个候选值
- 查询时按顺序尝试候选值，直到找到匹配结果

**执行逻辑：**

```python
for 条件组 in 条件组列表:
    for 候选值 in 条件组候选值:
        执行查询
        if 找到结果:
            添加结果并跳出当前条件组
            break
```

### 5.5.1 基础查询示例

```
\select 1001, 1002|1003 \from orders \select
```

```
-- 等效 SQL
SELECT * FROM orders WHERE primary_key IN (1001, 1002, 1003)
```

### 5.5.2 模糊查询 + 列选择

```
\select alice?, bob% \columns name, email \from users \select
```

```
-- 等效 SQL
SELECT name, email FROM users 
WHERE primary_key LIKE 'alice%' OR primary_key LIKE 'bob%'
```

### 5.5.3 复杂条件组合

```
\select 2023-01-%, 2023-02-?? \columns log_time, event_type \from system_logs \select
```

```
-- 等效 SQL
SELECT log_time, event_type FROM system_logs
WHERE primary_key LIKE '2023-01-%' 
   OR primary_key LIKE '2023-02-__'
```

### 5.5.4 多条件短路查询

```
\select ID123|ID456, NAME_A?|NAME_B \from customers \select
```

```
# 执行顺序：
1. 尝试 ID123 -> 找到则返回，否则尝试 ID456
2. 对找到的 ID 记录尝试 NAME_A% -> 找到则返回，否则尝试 NAME_B
```

## 注意事项

1. **类型转换**：
   - 插入数据时会自动进行类型转换
   - 转换失败时会记录警告并保留原始值
2. **主键限制**：
   - 查询语法目前仅支持单列主键表
   - 复合主键表需直接使用SQL查询
3. **事务管理**：
   - 批量插入自动使用事务
   - 单条插入默认自动提交
4. **性能优化**：
   - 批量插入时建议使用列表格式
   - 频繁查询时保持连接池活跃

------

## 简单的示例

```python
# 初始化
client = SQLiteClient('mydb.db')
parser = SQLiteParser(client, 'employees')

# 创建表
parser.create_table('employees', [
    {"name": "alias", "type": str, "primary": True},
    {"name": "name", "type": str},
    {"name": "salary", "type": float}
])

# 插入数据
parser.insert([
    {"alias": "joker", "name": "Alice", "salary": 85000.5},
    ["gosh", "Bob", 92000.0],
    ["player", "Charlie", 78000.0]
])

# 执行查询
results = parser.select(
    r"\select joker | Aalice, g?, not-exist \from employees \select"
)
print(results)
# 输出：
# [
#   {'alias':'joker', 'name':'Alice', 'salary':85000.5},  # 匹配第一个条件组
#   {'alias':'gosh', 'name':'Charlie', 'salary':78000.0} # 匹配第二个条件组
# ]
```