#!/bin/bash
# 容器啟動時先載入 ROS 2 環境，再執行傳進來的指令
set -e

source /opt/ros/humble/setup.bash

# 如果工作區已經 build 過，也一起載入
if [ -f /ws/install/setup.bash ]; then
    source /ws/install/setup.bash
fi

# exec 讓指令取代 shell 成為 PID 1，
# 這樣 docker stop 送出的 SIGTERM 才會直接送到 ROS 節點
exec "$@"
