# SQLite 数据库客户端使用文档

## 目录
1. [快速开始](#快速开始)
2. [连接管理](#连接管理)
3. [表操作](#表操作)
4. [数据操作](#数据操作)
   - [插入数据](#插入数据)
   - [批量插入](#批量插入)
   - [更新数据](#更新数据)
   - [查询数据](#查询数据)
5. [事务管理](#事务管理)
6. [注意事项](#注意事项)

---

## 快速开始

```python
from sqlite import SQLiteClient

# 初始化客户端（自动创建数据库文件）
db = SQLiteClient('mydatabase.db', pool_size=5)

# 创建表
db.execute(
    "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)",
    commit=True
)

# 插入数据
user_id = db.execute(
    "INSERT INTO users (name, email) VALUES (?, ?)",
    ('Alice', 'alice@example.com'),
    commit=True
)

# 查询数据
users = db.fetch_all("SELECT * FROM users")
print(users)  # [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}]
```

## 连接管理

### 初始化客户端

```python
# 参数说明：
# - database: 数据库文件路径
# - pool_size: 连接池大小（默认5）
# - **kwargs: 其他SQLite连接参数
db = SQLiteClient('mydatabase.db', pool_size=5, timeout=10)
```

### 关闭连接池

```python
# 程序退出时调用
db.pool.close_all()
```

## 表操作

### 创建表

```python
db.execute(
    '''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL
    )''',
    commit=True  # 必须显式提交DDL操作
)
```

### 删除表

```python
db.execute("DROP TABLE IF EXISTS products", commit=True)
```

------

## 数据操作

### 插入数据

**单条插入（返回插入ID）**

```
# 使用元组参数
product_id = db.execute(
    "INSERT INTO products (name, price) VALUES (?, ?)",
    ('Laptop', 999.99),
    commit=True
)

# 使用字典参数
product_id = db.execute(
    "INSERT INTO products (name, price) VALUES (:name, :price)",
    {'name': 'Phone', 'price': 599.99},
    commit=True
)
```

### 批量插入

```python
data = [
    ('Tablet', 299.99),
    ('Camera', 399.99),
    ('Headphones', 199.99)
]

db.executemany(
    "INSERT INTO products (name, price) VALUES (?, ?)",
    data,
    commit=True
)
```

### 更新数据

```python
# 单条更新
db.execute(
    "UPDATE products SET price = ? WHERE id = ?",
    (1099.99, 1),
    commit=True
)

# 批量更新建议使用事务（见事务管理章节）
```

### 查询数据

**获取所有结果**

```python
results = db.fetch_all("SELECT * FROM products WHERE price > ?", (500,))
"""
返回示例：
[
    {'id': 1, 'name': 'Laptop', 'price': 1099.99},
    {'id': 2, 'name': 'Phone', 'price': 599.99}
]
"""
```

------

## 事务管理

### 自动事务处理

```python
with db.transaction() as tx:
    tx.execute("UPDATE products SET price = ? WHERE id = ?", (899.99, 1))
    tx.execute("DELETE FROM products WHERE price < ?", (200,))
    # 事务会在退出上下文时自动提交
```

### 异常回滚

```python
try:
    with db.transaction() as tx:
        tx.execute("INSERT INTO products (name) VALUES (?)", ('Monitor',))
        raise Exception("模拟错误")  # 手动引发错误
except Exception as e:
    print("事务已自动回滚")
```

### 手动控制事务

```python
# 获取独立连接进行扩展操作
with db.connection() as conn:
    try:
        conn.execute('BEGIN')
        # 手动执行操作...
        conn.commit()
    except:
        conn.rollback()
        raise
```

------

## 注意事项

1. **连接管理**
   - 默认启用连接池（建议生产环境pool_size≥5）
   - 使用`commit=True`参数或事务管理器提交更改
   - 程序退出时建议调用`db.pool.close_all()`
2. **参数安全**
   - 始终使用参数化查询（防止SQL注入）
   - 支持元组和字典两种参数格式
3. **性能优化**
   - 批量操作使用`executemany`+事务
   - 频繁查询考虑添加适当索引
4. **错误处理**
   - 捕获`SQLiteError`及其子类异常
   - 检查日志文件定位问题（默认日志级别INFO）
5. **并发控制**
   - 多线程环境可直接使用（连接池线程安全）
   - 写操作建议使用事务保证原子性
6. **类型映射**
   - SQLite类型与Python类型自动转换
   - 查询结果以字典形式返回（保留列名）

```python
# 典型错误处理示例
try:
    db.execute("INVALID SQL")
except QueryExecutionError as e:
    print(f"查询执行失败: {str(e)}")
except ConnectionError as e:
    print(f"连接问题: {str(e)}")
```