from PyQt5.QtCore import QThread, QMutex, QWaitCondition, QMutexLocker, QRunnable


class FYCanRunnable(QRunnable):
    def __init__(self, wait_condition, mutex, parent=None):
        super().__init__()
        self.wait_condition = wait_condition
        self.mutex = mutex
        self.floating_yarn = None
        self.should_stop = False  # 标志位，表示线程是否应该停止

    def setFloatingYarn(self, floating_yarn):
        self.floating_yarn = floating_yarn

    def requestInterruption(self):
        self.should_stop = True

    def run(self):
        raise NotImplementedError("Subclasses should implement this!")
