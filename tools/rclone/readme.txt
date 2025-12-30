rclone版本下载地址：https://rclone.org/
ui版本下载：https://github.com/rclone/rclone-webui-react 放入ui目录
当前版本：Release v2.0.5

启动界面命令：
rclone rcd --rc-web-gui --rc-user=abc --rc-pass=abcd ./ui
杀死界面程序，如果终端被关闭：
netstat -ano | findstr ":5572"
taskkill /PID 22552 /F
