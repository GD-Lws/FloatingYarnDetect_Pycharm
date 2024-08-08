from PyQt5.QtCore import QThread, QMutex, QWaitCondition, QMutexLocker


class FYCanThread(QThread):
    """通用的 CAN 线程基类"""

    def __init__(self, wait_condition, mutex):
        super().__init__()
        self.wait_condition = wait_condition
        self.mutex = mutex
        self.floating_yarn = None  # 将在外部设置

    def set_floating_yarn(self, floating_yarn):
        self.floating_yarn = floating_yarn

    def run(self):
        """需要在子类中实现具体的线程逻辑"""
        raise NotImplementedError("Subclasses must implement this method")