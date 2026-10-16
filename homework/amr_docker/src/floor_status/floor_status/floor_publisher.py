"""
發布目前樓層到 /current_floor (std_msgs/Int32)。

現在先用參數設定樓層，之後可以換成真正的垂直狀態估測結果
（氣壓計、IMU 或其他方法），topic 名稱不變，網頁端就不用改。

改樓層（在另一個終端機）：
    ros2 param set /floor_publisher floor 2
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class FloorPublisher(Node):

    def __init__(self):
        super().__init__('floor_publisher')
        self.declare_parameter('floor', 1)
        self.declare_parameter('rate_hz', 1.0)

        self.pub = self.create_publisher(Int32, 'current_floor', 10)
        period = 1.0 / self.get_parameter('rate_hz').value
        self.timer = self.create_timer(period, self.publish_floor)
        self.get_logger().info('floor_publisher 已啟動，發布到 /current_floor')

    def publish_floor(self):
        msg = Int32()
        msg.data = self.get_parameter('floor').value
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FloorPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
