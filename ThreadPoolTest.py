import sys
import time
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, QTimer, QCoreApplication
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from queue import Queue


class WorkerSignals(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(str)


class DataReceiverWorker(QRunnable):
    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue

    def run(self):
        for i in range(5):  # Simulate receiving 5 pieces of data
            time.sleep(1)  # Simulate time delay in receiving data
            data = f"Data {i + 1}"
            self.data_queue.put(data)  # Put data into the queue
            print(f"Received: {data}")


class DataProcessorWorker(QRunnable):
    def __init__(self, data_queue, timeout=10):
        super().__init__()
        self.data_queue = data_queue
        self.timeout = timeout

    def run(self):
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > self.timeout:
                print("Processor timed out and will exit.")
                break

            try:
                data = self.data_queue.get(timeout=self.timeout - elapsed_time)  # Get data from the queue with timeout
            except Queue.Empty:
                break

            if data is None:  # Use None as a sentinel value to exit
                break

            # Simulate data processing
            time.sleep(2)
            print(f"Processed: {data}")
            self.data_queue.task_done()  # Mark task as done


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.thread_pool = QThreadPool()
        self.data_queue = Queue()
        print(f"Thread pool size: {self.thread_pool.maxThreadCount()}")

        # Start multiple data processing workers for parallel processing
        for _ in range(3):  # Number of processing threads
            processor_worker = DataProcessorWorker(self.data_queue, timeout=10)
            self.thread_pool.start(processor_worker)

    def initUI(self):
        self.button = QPushButton('Start Data Reception', self)
        self.button.clicked.connect(self.start_data_reception)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)

        self.setLayout(self.layout)
        self.setWindowTitle('Thread Pool Example')
        self.show()

    def start_data_reception(self):
        # Start the data receiver worker
        self.receiver_worker = DataReceiverWorker(self.data_queue)
        self.thread_pool.start(self.receiver_worker)

    def closeEvent(self, event):
        # Signal all processing workers to stop
        for _ in range(3):  # Number of processing threads
            self.data_queue.put(None)
        self.thread_pool.waitForDone()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
