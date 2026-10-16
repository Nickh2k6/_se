# syntax=docker/dockerfile:1
# ROS 2 Humble 開發容器：Nav2 + SLAM Toolbox + rosbridge
# Gazebo / RViz2 不放在容器內，留在主機原生執行
FROM ros:humble-ros-base

ARG DEBIAN_FRONTEND=noninteractive
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=1000

# 1) 系統套件
#    把 apt-get update、install、清快取寫在同一個 RUN，
#    才不會留下過期的套件清單、也不會讓 image 變肥
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-navigation2 \
        ros-humble-nav2-bringup \
        ros-humble-slam-toolbox \
        ros-humble-rosbridge-server \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-pip \
        sudo \
        git \
        nano \
    && rm -rf /var/lib/apt/lists/*

# 2) 建立和主機相同 UID/GID 的使用者
#    否則容器內 colcon build 產生的檔案在主機上會變成 root 擁有
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# 3) 工作區
#    build/install/log 會用 named volume 掛載；
#    先在 image 裡建好目錄並設定擁有者，volume 第一次建立時會沿用這個權限
WORKDIR /ws
RUN mkdir -p /ws/src /ws/build /ws/install /ws/log /ws/maps \
    && chown -R ${USERNAME}:${USERNAME} /ws

# 4) DDS 設定與 entrypoint
COPY docker/fastdds_udp.xml /etc/fastdds/fastdds_udp.xml
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && echo 'source /opt/ros/humble/setup.bash' >> /home/${USERNAME}/.bashrc \
    && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> /home/${USERNAME}/.bashrc

# 只用 UDP、關掉 shared memory，避免「看得到 topic 但收不到資料」
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/etc/fastdds/fastdds_udp.xml

USER ${USERNAME}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
