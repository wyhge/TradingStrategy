
python -m venv stock_env

stock_env\Scripts\activate

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

pip list | findstr "akshare pandas numpy"  # Windows











永久放宽（当前用户）	Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned	平衡安全与便利
• 永久生效，但仅影响当前用户。
• RemoteSigned 允许运行本地脚本，对网络下载的脚本则要求有数字签名。
永久放宽（所有用户）	Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned	需全局变更时使用
• 永久生效，影响本机所有用户。
• 需要管理员权限，普通用户可能无法执行。