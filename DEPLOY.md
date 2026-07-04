# 局域网部署说明

## 适用环境

- **服务器**：Windows 7 旗舰版（64位）
- **客户端**：局域网内任意设备的浏览器
- **数据库**：SQLite（无需额外安装）

---

## 一、服务器准备（一次性）

### 1.1 安装 Python 3.8.10

Win7 最高支持 Python 3.8.10，这是最后一个官方支持 Win7 的版本。

```
下载地址：https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe
```

安装时 **务必勾选** `Add Python to PATH`，其余默认即可。

### 1.2 拷贝项目

将整个 `kufang` 目录拷贝到服务器，例如 `D:\kufang`。

### 1.3 创建虚拟环境

```batch
cd /d D:\kufang
python -m venv .venv
```

---

## 二、启动服务

### 方式 A：直接运行（推荐测试阶段）

双击 `start_server.bat`，默认使用 **8000** 端口。

如需修改端口：
```batch
start_server.bat 9527
```

### 方式 B：注册为 Windows 服务（推荐长期运行）

使用 NSSM 注册为系统服务，实现开机自启、崩溃自动重启、后台静默运行。

```
1. 下载 nssm.exe（https://nssm.cc/download）
2. 将 nssm.exe 放到 C:\Windows\System32\
3. 以管理员身份打开 CMD，执行：

nssm install Kufang
```

在弹出的窗口中填写：

| 标签页 | 字段 | 值 |
|--------|------|-----|
| Application | Path | `D:\kufang\.venv\Scripts\python.exe` |
| Application | Arguments | `-m waitress --host=0.0.0.0 --port=8000 --threads=8 config.wsgi:application` |
| Application | Start directory | `D:\kufang` |
| Details | Display name | `库房管理系统` |

点击 `Install service`，然后启动：

```batch
nssm start Kufang
```

> 修改端口时，调整 `--port=8000` 为你想要的值即可。

---

## 三、防火墙放行

Win7 默认防火墙会拦截 8000 端口，需要添加放行规则。

**以管理员身份** 打开 CMD：

```batch
netsh advfirewall firewall add rule name="Kufang" dir=in action=allow protocol=TCP localport=8000
```

> 如果换了端口，把 `8000` 改成对应端口号。

---

## 四、客户端访问

服务器 IP 查看方法：在服务器上打开 CMD，输入 `ipconfig`，找到 IPv4 地址。

局域网内其他电脑浏览器访问：

```
http://192.168.1.100:8000          （示例 IP，换成实际地址）
```

演示账号（密码统一 `demo123`）：

| 用户名 | 角色 |
|--------|------|
| `admin` | 超级管理员 |
| `zhangsan` / `lisi` | 主机组操作员 |
| `wangwu` / `zhaoliu` | 冷却组操作员 |
| `sunqi` / `zhouba` | 电力组操作员 |

---

## 五、停止服务

- **双击 bat 启动的** → 按 `Ctrl+C` 或在 CMD 窗口点 X
- **NSSM 注册的服务** → `nssm stop Kufang`

---

## 六、日常维护

### 数据备份

SQLite 数据库是单文件，直接复制即可：

```batch
copy D:\kufang\db.sqlite3 D:\backup\db_%date:~0,4%%date:~5,2%%date:~8,2%.sqlite3
```

### 更新代码

```batch
cd /d D:\kufang
git pull
.venv\Scripts\activate
python manage.py migrate
```

### 重启服务

```batch
nssm restart Kufang
```

---

## 七、端口对照

| 端口 | 用途 |
|------|------|
| 8000 | 默认端口（可在 `start_server.bat` 或 NSSM 参数中修改） |
