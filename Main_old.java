package com.example.myapplication;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Camera;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.SurfaceTexture;
import android.graphics.YuvImage;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CameraMetadata;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.media.CamcorderProfile;
import android.media.Image;
import android.media.ImageReader;
import android.media.MediaRecorder;
import android.net.Uri;
import android.nfc.Tag;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.provider.MediaStore;
import android.util.Log;
import android.util.Range;
import android.util.Size;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.TextureView;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ListView;
import android.widget.PopupWindow;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.Manifest;

import org.opencv.android.OpenCVLoader;
import org.opencv.android.Utils;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import android.graphics.Rect;
import android.widget.Toast;

import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;
import com.hoho.android.usbserial.util.SerialInputOutputManager;

import org.opencv.imgproc.Imgproc;
import org.opencv.videoio.VideoCapture;
import org.opencv.videoio.Videoio;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.lang.reflect.Executable;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;

import static com.example.myapplication.MyUtil.getBufferedWriter;


public class MainActivity extends Activity implements  View.OnClickListener,TextureView.SurfaceTextureListener {
    private static final String FAG = "FileTest";
    private static final String CAG = "CameraDebug";
    private static final String IAG = "IOSerial";

    private static final int REQUEST_CODE_PICK_VIDEOFile = 1;
    private static final int REQUEST_CODE_PICK_DIRECTORY = 123;

    // Used to load the 'myapplication' library on application startup.
    static {
        System.loadLibrary("myapplication");
    }
    private Button button_file, button_start, button_serial, button_record;
//    ROI区域
    private EditText et_rx,et_ry,et_rw,et_rh, et_lx,et_ly,et_lw,et_lh;
    private EditText[] et_roi_array,et_camera_array,et_detect_array;
//  相机参数
    private EditText et_exposureTime, et_ISO, et_focusdistance, et_zoomare, et_recordFileName;
    private EditText et_camera_par1, et_camera_par2, et_camera_par3;
    private ExecutorService executors;
    private static Bitmap inBitmap = null;
//  捕获会话
    private CameraCaptureSession mCaptureSession;
//  用于控制多个线程对共享资源的访问，以确保同一时间只有一个线程可以访问相机设备
    private long camera_exposureTime = new Long(7104250);
    private int camera_Iso = 1200;
    private float camera_focusDistance = 4.12f, camera_zoomRatio = 6.0F;
    private CameraCharacteristics cameraCharacteristics;
    private CameraManager cameraManager;
    private HandlerThread mCameraThread, mImageThread;
    private Handler mCameraHandler, mImageHandler;
    private String save_file_path = null;
    private String cameraId;
    private CameraDevice mCameraDevice;
    private CaptureRequest.Builder mPreviewBuilder;
    private Semaphore mCameraOpenCloseLock = new Semaphore(1);
    private ImageReader mImageReader;
//    是否设置ROI
    private boolean roi_flag = false;
    private boolean detect_flag = false;
    //    文件选取或者相机获取
    private int[] arr_roi1 = new int[]{512, 200, 722, 380};
    private int[] arr_roi2 = new int[]{512, 400, 662, 580};
    private float[] detect_par_arr = new float[]{40.0f, 255.0f, 0.4f};

    private TextureView mCameraPreview,mResultPreview;
    private Size mPreviewSize;
    private TextView tv_machine_row;
    private MyUtil myUtil;
    private Spinner modeSelect;
//    视频录制

//    串口配置
    private UsbManager usbManager = null;
    private TextView tv_rec;
    private ListView lv_device;
    private ListItem device_select = null;
    private static final int WRITE_WAIT_MILLIS = 2000;
    private static final int READ_WAIT_MILLIS = 2000;
    private static final String INTENT_ACTION_GRANT_USB = BuildConfig.APPLICATION_ID + ".GRANT_USB";
    private final ArrayList listItems = new ArrayList<>();
    private ArrayAdapter listAdapter;
    private int baudRate = 19200;
    private boolean serialOpenFlag = false;
    private boolean recordFlag = false;
    private UsbSerialPort usbSerialPort;
    private UsbDeviceConnection usbConnection;
    private enum UsbPermission { Unknown, Requested, Granted, Denied }
    private MainActivity.UsbPermission usbPermission = MainActivity.UsbPermission.Unknown;
    private SerialInputOutputManager usbIoManager;
    private int[] baudRate_array = {9600, 19200, 38400, 57600, 76800, 115200};
    private Surface resultSurface;
    private String recordFileName = "测试文件";
    private String getSave_file_path = "";
    private int yarnRow = 0;
    private int holdRow = 0;
    private SharedPreferences cameraSP;

    private enum serialState {
        CLOSE,
        OPEN,
        ACTIVE,
        EDIT
    }
    private serialState currentState = serialState.CLOSE;

    private enum appMode{
        RECORD,
        DETECT,
        Compare
    }
    private appMode currentMode = appMode.DETECT;
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        initView();
        getSave_file_path = getExternalCacheDir().getAbsolutePath() + "/";
        OpenCVLoader.initDebug(false);
        cameraSP = getSharedPreferences("CameraPreferences", Context.MODE_PRIVATE);
        if (myUtil.checkPermissions(MainActivity.this)) {
            // 权限已授予，执行您的逻辑
//            openFilePicker();
            Toast.makeText(this, "浮纱检测程序", Toast.LENGTH_SHORT).show();
        }else {
            Toast.makeText(this, "检测权限未授权", Toast.LENGTH_SHORT).show();
        }
        cameraManager = (CameraManager)getApplication().getSystemService(Context.CAMERA_SERVICE);
        try{
            cameraId = cameraManager.getCameraIdList()[0];
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

//    初始界面
    private void initView(){
        button_file = findViewById(R.id.button_file);
        button_start = findViewById(R.id.button_start);
        button_record = findViewById(R.id.button_record);
        button_serial = findViewById(R.id.button_serial);

        mCameraPreview = findViewById(R.id.textureview_camera);
        mCameraPreview.setSurfaceTextureListener(this);
        mResultPreview = findViewById(R.id.textureview_result);
        mResultPreview.setSurfaceTextureListener(this);
        tv_machine_row = findViewById(R.id.tv_machine_row);

        modeSelect = findViewById(R.id.Spinner_mode);

        modeSelect.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                switch (position){
                    case 0:{
                        currentMode = appMode.DETECT;
                        Toast.makeText(MainActivity.this, "Change to Detect Mode！", Toast.LENGTH_SHORT).show();
                    }break;
                    case 1:{
                        currentMode = appMode.Compare;
                        Toast.makeText(MainActivity.this, "Change to Compare Mode！", Toast.LENGTH_SHORT).show();
                    }break;
                    case 2:{
                        currentMode = appMode.RECORD;
                        Toast.makeText(MainActivity.this, "Change to Record Mode！", Toast.LENGTH_SHORT).show();
                    }break;
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {

            }
        });

        button_start.setOnClickListener(this);
        button_file.setOnClickListener(this);
        button_serial.setOnClickListener(this);
        button_record.setOnClickListener(this);

        Spinner spinnerParSet = findViewById(R.id.Spinner_Setpar);
        spinnerParSet.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                Dialog_set(position);
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
    }

    @Override
    public void onClick(View v) {
        int id = v.getId();
        if (id == R.id.button_start){
            if (!detect_flag)
            {
                if(roi_flag){
                    Toast.makeText(MainActivity.this, "开始检测", Toast.LENGTH_SHORT).show();
                    button_start.setText("STOP");
                    detect_flag = true;
                }else {
                    Toast.makeText(MainActivity.this, "Roi未设置", Toast.LENGTH_SHORT).show();
                }
            }else {
                Toast.makeText(MainActivity.this, "停止检测", Toast.LENGTH_SHORT).show();
                button_start.setText("START");
                detect_flag = false;
            }
        } else if (id == R.id.button_serial) {
            showPopupWindow();
            Toast.makeText(MainActivity.this, "串口监听", Toast.LENGTH_SHORT).show();
        } else if (id == R.id.button_file) {
            openFilePicker();
            Toast.makeText(MainActivity.this, "文件选择", Toast.LENGTH_SHORT).show();
        } else if (id == R.id.button_record) {
            if (!recordFlag){
                recordFlag = true;
                button_record.setText("STOP");
            }else {
                recordFlag = false;
                button_record.setText("RECORD");
            }
        }
    }

//   检查设置的参数
    private boolean checkCameraPar(){
        Log.e(CAG,"参数设置错误");
        return false;
    }
    private void openFilePicker(){
        Intent intent= new Intent(Intent.ACTION_GET_CONTENT);
        intent.setType("video/*");
        startActivityForResult(intent, REQUEST_CODE_PICK_VIDEOFile);
    }

//    @Override
//    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
//        super.onActivityResult(requestCode, resultCode, data);
//        if (requestCode == REQUEST_CODE_PICK_VIDEOFile && resultCode == RESULT_OK){
//            Uri videoUri = data.getData();
//            Log.d(FAG, "Video URI: " + videoUri.toString());
//            String video_path = getRealPathFromURI(videoUri);
//            if (video_path != null){
//                Log.d(FAG, "Video Path: " + video_path);
//                if(myUtil.check_video_permission(video_path)) {
//                    save_file_path = video_path;
//                }
//            }else {
//                Log.d("VideoUri", "Video URI: " + videoUri.toString());
//            }
//        }
//    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_PICK_DIRECTORY && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            if (uri != null) {
                String folderPath = uri.getPath();
                // 现在你可以使用文件夹路径来读取文件夹中的文件
                Toast.makeText(MainActivity.this, "GetFoldPath", Toast.LENGTH_SHORT).show();
//                readBmpFilesInFolder(folderPath);
            }
        }
    }

    private void readBmpFilesInFolder(String folderPath) {
        File folder = new File(folderPath);
        if (folder.exists() && folder.isDirectory()) {
            File[] files = folder.listFiles();
            if (files != null) {
                for (File file : files) {
                    if (file.isFile() && file.getName().toLowerCase().endsWith(".bmp")) {
                        // 这里处理bmp文件
                         file.getAbsolutePath();
                    }
                }
            }
        }
    }

    private String getRealPathFromURI(Uri contentUri) {
        String[] projection = {MediaStore.Video.Media.DATA};
        Cursor cursor = getContentResolver().query(contentUri, projection, null, null, null);
        if (cursor != null) {
            int columnIndex = cursor.getColumnIndexOrThrow(MediaStore.Video.Media.DATA);
            cursor.moveToFirst();
            String path = cursor.getString(columnIndex);
            cursor.close();
            return path;
        }
        return null;
    }

// 当 SurfaceTexture 对象关联的 Surface 已经准备好，可以开始渲染内容时调用
//    width 和 height：表示 SurfaceTexture 的宽度和高度
    @Override
    public void onSurfaceTextureAvailable(@NonNull SurfaceTexture surface, int width, int height) {
        if (surface == mCameraPreview.getSurfaceTexture()) {
            startBackgroundThread();
            openCamera(width, height);
            mImageReader = ImageReader.newInstance(width, height, ImageFormat.YUV_420_888, 52);
            mImageReader.setOnImageAvailableListener(mOnImageAvailableListener, mImageHandler);
        }
    }

    @Override
    public void onSurfaceTextureSizeChanged(@NonNull SurfaceTexture surface, int width, int height) {

    }
    @Override
    public boolean onSurfaceTextureDestroyed(@NonNull SurfaceTexture surface) {
        if (surface == mCameraPreview.getSurfaceTexture()) {
            closeCamera();
        }
        return false;
    }

    @Override
    public void onSurfaceTextureUpdated(@NonNull SurfaceTexture surface) {

    }

//  捕获过程完成时调用的
    private CameraCaptureSession.CaptureCallback mCaptureCallback = new CameraCaptureSession.CaptureCallback() {
        @Override
        public void onCaptureCompleted(@NonNull CameraCaptureSession session, @NonNull CaptureRequest request, @NonNull TotalCaptureResult result) {
            super.onCaptureCompleted(session, request, result);
            // Retrieve exposure time from the result
            float real_exposureTime = result.get(CaptureResult.SENSOR_EXPOSURE_TIME);
            Range real_fps_Range = result.get(CaptureResult.CONTROL_AE_TARGET_FPS_RANGE);
            float real_Iso_value = result.get(CaptureResult.SENSOR_SENSITIVITY);
            float real_focusDistance = result.get(CaptureResult.LENS_FOCUS_DISTANCE);
            if (real_exposureTime != 0) {
                Log.i("camera_info", "ETR: " + real_exposureTime+ " FPS: " + real_fps_Range + " FDR: " + real_focusDistance + " ISO: " + real_Iso_value);
            }
        }
    };


//    这个回调用于监听相机设备的状态变化
    private CameraDevice.StateCallback mStateCallback = new CameraDevice.StateCallback() {
        @Override
        public void onOpened(@NonNull CameraDevice cameraDevice) {
            mCameraDevice = cameraDevice;
            startPreview();
            mCameraOpenCloseLock.release();
        }

        @Override
        public void onDisconnected(@NonNull CameraDevice cameraDevice) {
            mCameraOpenCloseLock.release();
            cameraDevice.close();
            mCameraDevice = null;
        }

        @Override
        public void onError(@NonNull CameraDevice cameraDevice, int error) {
            mCameraOpenCloseLock.release();
            cameraDevice.close();
            mCameraDevice = null;
        }
    };

    private Rect getRect(float Input_zoomRatio){
        Rect sensorSize = cameraCharacteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);
        int centerX = sensorSize.centerX();
        int centerY = sensorSize.centerY();
        int deltaX = (int) ((sensorSize.width() / (2 * Input_zoomRatio)) + 0.5f);
        int deltaY = (int) ((sensorSize.height() / (2 * Input_zoomRatio)) + 0.5f);
        Rect outputRect = new Rect(
                Math.max(centerX - deltaX, 0),
                Math.max(centerY - deltaY, 0),
                Math.min(centerX + deltaX, sensorSize.width() - 1),
                Math.min(centerY + deltaY, sensorSize.height() - 1));
        return outputRect;
    }

//    设置相机参数
    private void setCameraPar(){
        Range<Integer> fpsRange = new Range(240, 240);
        mPreviewBuilder.set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, fpsRange);
        mPreviewBuilder.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF);
        mPreviewBuilder.set(CaptureRequest.CONTROL_MODE, CameraMetadata.CONTROL_MODE_OFF);
        mPreviewBuilder.set(CaptureRequest.LENS_FOCUS_DISTANCE, camera_focusDistance);
        mPreviewBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, camera_exposureTime);
        mPreviewBuilder.set(CaptureRequest.SCALER_CROP_REGION, getRect(camera_zoomRatio));
        mPreviewBuilder.set(CaptureRequest.SENSOR_SENSITIVITY, camera_Iso);
        Log.d(CAG, "相机参数设置");
    }
    private void startPreview(){
        if (null == mCameraDevice) {
            Log.e(CAG, "CameraDevice is null");
            return;
        }
        try {
            Log.i(CAG, "申请预览");
            // 设置为手动模式
            mPreviewBuilder = mCameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            SurfaceTexture texture = mCameraPreview.getSurfaceTexture();
            texture.setDefaultBufferSize(mPreviewSize.getWidth(), mPreviewSize.getHeight());
            Surface surface = new Surface(texture);
            setCameraPar();
            mPreviewBuilder.addTarget(surface);
//            图像处理
            mPreviewBuilder.addTarget(mImageReader.getSurface());
            mCameraDevice.createCaptureSession(Arrays.asList(surface,mImageReader.getSurface()), new CameraCaptureSession.StateCallback() {
                @Override
                public void onConfigured(@NonNull CameraCaptureSession cameraCaptureSession) {
                    mCaptureSession = cameraCaptureSession;
                    Log.d(CAG, "createCaptureSession onConfigured");
                    try {
                        mCaptureSession.setRepeatingRequest(mPreviewBuilder.build(), mCaptureCallback, mCameraHandler);
                    } catch (CameraAccessException e) {
                        e.printStackTrace();
                    }
                }
                @Override
                public void onConfigureFailed(@NonNull CameraCaptureSession cameraCaptureSession) {
                    Toast.makeText(getApplicationContext(), "Failed", Toast.LENGTH_SHORT).show();
                }
            }, mCameraHandler);
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private Bitmap resultBitmap = null, grayscaleBitmap = null;
    private final ImageReader.OnImageAvailableListener mOnImageAvailableListener = new ImageReader.OnImageAvailableListener() {
        @Override
        public void onImageAvailable(ImageReader reader) {
            Image readerImage = reader.acquireLatestImage();
            if (readerImage != null) {
                Image.Plane[] planes = readerImage.getPlanes();
                // 获取 Y 分量的信息
                Image.Plane yPlane = planes[0];
                ByteBuffer yBuffer = yPlane.getBuffer();
                int yPixelStride = yPlane.getPixelStride();
                int yRowStride = yPlane.getRowStride();
                int yWidth = readerImage.getWidth();
                int yHeight = readerImage.getHeight();

                // 创建字节数组来存储 Y 数据
                byte[] yData = new byte[yBuffer.remaining()];
                yBuffer.get(yData);

                // 创建 Mat 对象
                Mat yMat = new Mat(yHeight + yHeight / 2, yWidth, CvType.CV_8UC1);
                int offset = 0;
                for (int row = 0; row < yHeight; row++) {
                    yMat.put(row, 0, yData, offset, yWidth);
                    offset += yRowStride;
                }

                // 转换为灰度图
                Mat grayscaleMat = new Mat();
                Imgproc.cvtColor(yMat, grayscaleMat, Imgproc.COLOR_YUV2GRAY_NV21);

                // 创建 Bitmap 对象
                Bitmap bitmap = Bitmap.createBitmap(yWidth, yHeight, Bitmap.Config.ARGB_8888);

                // 将灰度图像复制到 Bitmap 中
                Utils.matToBitmap(grayscaleMat, bitmap);

                // 在 UI 线程中更新 ImageView
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        drawBitmapToSurfaceTexture(bitmap);
                    }
                });

                // 释放 Image 资源
                readerImage.close();
            }
        }
    };

    private void drawBitmapToSurfaceTexture(Bitmap bitmap) {
        // 获取 SurfaceTexture
        SurfaceTexture surfaceTexture = mResultPreview.getSurfaceTexture();
        if (surfaceTexture == null) {
            return;
        }

        // 将 SurfaceTexture 与当前线程关联
        surfaceTexture.setDefaultBufferSize(bitmap.getWidth(), bitmap.getHeight());
        resultSurface = new Surface(surfaceTexture);

        try {
            // 开始绘制
            Canvas canvas = resultSurface.lockCanvas(null);
            if (canvas != null) {
                // 清除画布
                canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR);

                // 绘制 Bitmap
                canvas.drawBitmap(bitmap, 0, 0, null);

                // 结束绘制
                resultSurface.unlockCanvasAndPost(canvas);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            resultSurface.release();
        }
    }

//    index:0->camera;1->Roi;2->Detect
    private void Dialog_set(int index) {
        LayoutInflater inflater = (LayoutInflater) getSystemService(Context.LAYOUT_INFLATER_SERVICE);
        View dialogView;
        AlertDialog.Builder builder;
        switch (index){
            case 0:{
                Toast.makeText(MainActivity.this, "摄像头参数设置", Toast.LENGTH_SHORT).show();
                dialogView = inflater.inflate(R.layout.dig_camera_par_set, null);
                builder = mygetBuilder(MainActivity.this, dialogView,index);
            }break;
            case 1:{
                Toast.makeText(MainActivity.this, "ROI窗口设置", Toast.LENGTH_SHORT).show();
                dialogView = inflater.inflate(R.layout.dig_roi_set, null);
                builder = mygetBuilder(MainActivity.this, dialogView,index);
            }break;
            case 2:{
                Toast.makeText(MainActivity.this, "识别参数设置", Toast.LENGTH_SHORT).show();
                dialogView = inflater.inflate(R.layout.dig_detect_par_set, null);
                builder = mygetBuilder(MainActivity.this, dialogView,index);
            }break;
            case 3:{
                Toast.makeText(MainActivity.this, "录制文件名设置", Toast.LENGTH_SHORT).show();
                dialogView = inflater.inflate(R.layout.dig_file_name, null);
                builder = mygetBuilder(MainActivity.this, dialogView,index);
            }break;
            default:{
                dialogView = inflater.inflate(R.layout.dig_camera_par_set, null);
                builder = mygetBuilder(MainActivity.this, dialogView,index);
                Toast.makeText(MainActivity.this, "Input index error!", Toast.LENGTH_SHORT).show();
            }
        }
        // 显示对话框
        AlertDialog dialog = builder.create();
        dialog.show();
    }


    private PopupWindow popupWindow;
    private void showPopupWindow() {
        // 创建LayoutInflater实例
        LayoutInflater inflater = (LayoutInflater) getSystemService(Context.LAYOUT_INFLATER_SERVICE);

        // 填充PopupWindow布局
        View popupView = inflater.inflate(R.layout.activity_serial_test, null);
        // 创建PopupWindow对象
        popupWindow = new PopupWindow(popupView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT, true);
        // 设置PopupWindow的背景，这样点击外部区域就可以关闭PopupWindow
        popupWindow.setBackgroundDrawable(new ColorDrawable(Color.WHITE));
//        popupWindow.setOutsideTouchable(true);
        // 设置PopupWindow的动画效果（可选）
        popupWindow.setAnimationStyle(android.R.style.Animation_Dialog);
        // 显示PopupWindow
        popupWindow.showAtLocation(getWindow().getDecorView(), Gravity.CENTER, 0, 0);
        tv_rec = popupView.findViewById(R.id.tv_rec);
        // 处理PopupWindow中的控件事件
        listAdapter = new ArrayAdapter(MainActivity.this, 0, listItems) {
            @NonNull
            @Override
            public View getView(int position, View view, @NonNull ViewGroup parent) {
                ListItem item = (ListItem) listItems.get(position);
                if (view == null)
                    view = MainActivity.this.getLayoutInflater().inflate(R.layout.device_list_item, parent, false);
                TextView text1 = view.findViewById(R.id.text1);
                TextView text2 = view.findViewById(R.id.text2);
                if(item.driver == null)
                    text1.setText("<no driver>");
                else if(item.driver.getPorts().size() == 1)
                    text1.setText(item.driver.getClass().getSimpleName().replace("SerialDriver",""));
                else
                    text1.setText(item.driver.getClass().getSimpleName().replace("SerialDriver","")+", Port "+item.port);
                text2.setText(String.format(Locale.US, "Vendor %04X, Product %04X", item.device.getVendorId(), item.device.getProductId()));
                return view;
            }
        };
        lv_device = popupView.findViewById(R.id.lv_derive);
        lv_device.setAdapter(listAdapter);
        lv_device.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                MainActivity.ListItem item = (ListItem) listItems.get(position);
                if(item.driver == null) {
                    Toast.makeText(MainActivity.this, "no driver", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(MainActivity.this, "Select driverId" + item.device.getDeviceId() + "port" +  item.port + "baud" + baudRate, Toast.LENGTH_SHORT).show();
                    device_select = item;
                }
            }
        });
        Button backButton = popupView.findViewById(R.id.bt_Back);
        backButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // 关闭PopupWindow
                Toast.makeText(MainActivity.this, "关闭窗口", Toast.LENGTH_SHORT).show();
                popupWindow.dismiss();
            }
        });
        Button openButton = popupView.findViewById(R.id.bt_open);
        openButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                serialOpen();
            }
        });

        Button refreshButton = popupView.findViewById(R.id.bt_refresh);
        refreshButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                serialRefresh();
                Toast.makeText(MainActivity.this, "串口设备刷新", Toast.LENGTH_SHORT).show();
            }
        });

        EditText et_send = popupView.findViewById(R.id.et_send);
        Button sendButton = popupView.findViewById(R.id.bt_send);
        sendButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String send_string = et_send.getText().toString();
                serialSendData(send_string);
            }
        });
        Button bt_state = popupView.findViewById(R.id.bt_STATE);
        bt_state.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Toast.makeText(MainActivity.this, "Now Serial State is " + currentState, Toast.LENGTH_SHORT).show();
            }
        });
        Spinner spinner_baudRate = popupView.findViewById(R.id.Spinner_baud);
        spinner_baudRate.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                baudRate = baudRate_array[position];
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
    }

    @NonNull
    private AlertDialog.Builder mygetBuilder(Context context, View dialogView, int dialog_index) {
        AlertDialog.Builder builder = new AlertDialog.Builder(context);
        if (dialog_index == 0)builder.setTitle("相机参数设置");
        else if(dialog_index == 1)builder.setTitle("ROI区域设置");
        else if (dialog_index == 2)builder.setTitle("检测参数设置");
        else if (dialog_index == 3)builder.setTitle("录制文件名设置");
        builder.setView(dialogView);
        if(dialog_index == 0) {
            et_exposureTime = dialogView.findViewById(R.id.et_exposuretime);
            et_focusdistance = dialogView.findViewById(R.id.et_focusdistance);
            et_zoomare = dialogView.findViewById(R.id.et_zoomarea);
            et_ISO = dialogView.findViewById(R.id.et_iso);
            et_camera_array = new EditText[]{et_exposureTime, et_ISO, et_focusdistance, et_zoomare};
            if (roi_flag) {
                et_exposureTime.setText(String.valueOf(camera_exposureTime));
                et_focusdistance.setText(String.valueOf(camera_focusDistance));
                et_zoomare.setText(String.valueOf(camera_zoomRatio));
                et_ISO.setText(String.valueOf(camera_Iso));
            }
            Log.d(CAG, "camera_dig");
        } else if (dialog_index == 1) {
            et_rx = dialogView.findViewById(R.id.et_roi_r_x);
            et_ry = dialogView.findViewById(R.id.et_roi_r_y);
            et_rw = dialogView.findViewById(R.id.et_roi_r_w);
            et_rh = dialogView.findViewById(R.id.et_roi_r_h);

            et_lx = dialogView.findViewById(R.id.et_roi_l_x);
            et_ly = dialogView.findViewById(R.id.et_roi_l_y);
            et_lw = dialogView.findViewById(R.id.et_roi_l_w);
            et_lh = dialogView.findViewById(R.id.et_roi_l_h);
            et_roi_array = new EditText[]{et_rx, et_ry, et_rw, et_rh, et_lx, et_ly, et_lw, et_lh};
            for (int j = 0; j < 8; j++) {
                if (j < 4) {
                    if (j > 1) {
                        et_roi_array[j].setText((arr_roi1[j] - arr_roi1[j - 2]) + "");
                    } else {
                        et_roi_array[j].setText(arr_roi1[j] + "");
                    }
                } else {
                    if (j > 5) {
                        et_roi_array[j].setText((arr_roi2[j - 4] - arr_roi2[j - 2 - 4]) + "");
                    } else {
                        et_roi_array[j].setText(arr_roi2[j - 4] + "");
                    }
                }
            }
        } else if (dialog_index == 2) {
            et_camera_par1 = dialogView.findViewById(R.id.et_par_one);
            et_camera_par2 = dialogView.findViewById(R.id.et_par_two);
            et_camera_par3 = dialogView.findViewById(R.id.et_par_three);
            et_detect_array = new EditText[]{et_camera_par1, et_camera_par2, et_camera_par3};
            for (int i = 0; i < 3; i++) {
                et_detect_array[i].setText(String.valueOf(detect_par_arr[i]));
            }
        } else if (dialog_index == 3) {
            et_recordFileName = dialogView.findViewById(R.id.et_recordFile);
            Button bt_saveCameraPar = dialogView.findViewById(R.id.button_parsave);
            Button bt_reloadCameraPar = dialogView.findViewById(R.id.button_parreload);
            bt_saveCameraPar.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    String saveString = saveCameraPar();
                    Toast.makeText(MainActivity.this, saveString, Toast.LENGTH_SHORT).show();
                }
            });
            bt_reloadCameraPar.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    camera_Iso = cameraSP.getInt("Iso_value",camera_Iso);
                    camera_focusDistance = cameraSP.getFloat("focusDistance",camera_focusDistance);
                    camera_exposureTime = cameraSP.getLong("exposureTime", camera_exposureTime);
                    camera_zoomRatio = cameraSP.getFloat("zoomRatio", camera_zoomRatio);
                    String[] getRoiString = cameraSP.getString("roiArray", "").split(",");
                    if (getRoiString.length > 0) {
                        for (int i = 0; i < 8; i++) {
                            if (i<4)arr_roi1[i] = Integer.parseInt(getRoiString[i]);
                            else arr_roi2[i-4] = Integer.parseInt(getRoiString[i]);
                        }
                    }
                    String[] getDetString = cameraSP.getString("detArray","").split(",");
//                    if (getDetString.length > 0) {
//                        for (int i = 0; i < 3; i++) {
//                            detect_par_arr[i] = Float.parseFloat(getRoiString[i]);
//                        }
//                    }
//                    editor.putFloat("det_par_0",detect_par_arr[0]);
                    detect_par_arr[0] = cameraSP.getFloat("det_par_0", 30.0f);
                    detect_par_arr[1] = cameraSP.getFloat("det_par_1", 255.0f);
                    detect_par_arr[2] = cameraSP.getFloat("det_par_2", 0.3f);
                    Toast.makeText(MainActivity.this, "加载参数成功", Toast.LENGTH_SHORT).show();
                }
            });

        }

        builder.setPositiveButton("OK", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialogInterface, int i) {
                if(dialog_index == 0) {
                    try {
                        Long temp_camera_exposureTime = Long.parseLong(et_camera_array[0].getText().toString());
                        int temp_camera_Iso = Integer.parseInt(et_camera_array[1].getText().toString());
                        float temp_camera_focusDistance = Float.parseFloat(et_camera_array[2].getText().toString());
                        float temp_camera_zoomRatio = Float.parseFloat(et_camera_array[3].getText().toString());

                        if (myUtil.isCameraParametersValid(temp_camera_exposureTime, temp_camera_Iso, temp_camera_focusDistance, temp_camera_zoomRatio)){
                            camera_exposureTime = temp_camera_exposureTime;
                            camera_Iso = temp_camera_Iso;
                            camera_focusDistance = temp_camera_focusDistance;
                            camera_zoomRatio = temp_camera_zoomRatio;
                            try {
                                setCameraPar();
                                mCaptureSession.setRepeatingRequest(mPreviewBuilder.build(), mCaptureCallback, mCameraHandler);
                            }catch (CameraAccessException e)
                            {
                                e.printStackTrace();
                            }
                        }else {
                            Toast.makeText(MainActivity.this,"Camera input out of range!",Toast.LENGTH_SHORT).show();
                        }
                    }catch (NumberFormatException e){
                        Toast.makeText(context, "输入类型有问题", Toast.LENGTH_SHORT).show();
                    }
                }
                else if (dialog_index == 1) {
                    for (int j = 0; j < 8; j++) {
                        int temp = Integer.parseInt(et_roi_array[j].getText().toString());
                        try {
                            if (j < 4){
                                if (j > 1){
                                    arr_roi1[j] = temp + arr_roi1[j-2];
                                }else {
                                    arr_roi1[j] = temp;
                                }
                            }
                            else {
                                if (j > 5){
                                    arr_roi2[j-4] = temp + arr_roi2[j-2-4];
                                }else {
                                    arr_roi2[j-4] = temp;
                                }
                            }
                        }catch (NumberFormatException e)
                        {
                            roi_flag = false;
                            Toast.makeText(context, "输入类型有问题", Toast.LENGTH_SHORT).show();
                            break;
                        }
                        catch (ArrayIndexOutOfBoundsException e){
                            roi_flag = false;
                            Toast.makeText(context, "输入长度有问题" + j + " " + (j-2), Toast.LENGTH_SHORT).show();
                            break;
                        }
                    }
                    roi_flag = true;
                }
                else if (dialog_index == 2){
                    for (int j = 0; j < 3; j++) {
                        detect_par_arr[j] = Float.parseFloat(et_detect_array[j].getText().toString());
                    }
                } else if (dialog_index == 3) {
                    recordFileName = et_recordFileName.getText().toString();
                    if (myUtil.createFolder(getSave_file_path+"/"+recordFileName))
                    {
                        yarnRow = 0;
                        Toast.makeText(MainActivity.this, "新建文件夹:" + recordFileName, Toast.LENGTH_SHORT).show();

                    }
                }
                dialogInterface.dismiss();
            }
        });
        builder.setNegativeButton("Cancel", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialogInterface, int i) {
                // 用户点击取消，关闭对话框
                dialogInterface.dismiss();
            }
        });
        return builder;
    }


    private String saveCameraPar(){
        String result_string = "";
        SharedPreferences.Editor editor = cameraSP.edit();
        editor.putInt("Iso_value", camera_Iso);
        editor.putFloat("focusDistance", camera_focusDistance);
        editor.putLong("exposureTime", camera_exposureTime);
        editor.putFloat("zoomRatio", camera_zoomRatio);
        result_string = result_string + "Iso:"+ camera_Iso + " Fd:" + camera_focusDistance + " ET:" + camera_exposureTime + " ZR:" + camera_zoomRatio;
        result_string = result_string + "\n";
        String roi_string = "";
//        String det_string = "";
        for (int i = 0; i < 8; i++) {
            if (i < 4) roi_string = roi_string + arr_roi1[i]+",";
            else {
                roi_string = roi_string + arr_roi2[i - 4] + ",";
            }
        }
        result_string = result_string + " Ro:" + roi_string + "\n";
        editor.putString("roiArray", roi_string);
//        for (int i = 0; i < 3; i++) {
//            det_string = det_string + String.valueOf(detect_par_arr) + ",";
//        }
//        result_string = result_string + " De:" + det_string + "\n";
//        editor.putString("detArray", det_string);
        editor.putFloat("det_par_0",detect_par_arr[0]);
        editor.putFloat("det_par_1",detect_par_arr[1]);
        editor.putFloat("det_par_2",detect_par_arr[2]);
        result_string = result_string + String.format("%.2f", detect_par_arr[0]) + "," + String.format("%.2f", detect_par_arr[1]) + "," + String.format("%.2f", detect_par_arr[2]);
        editor.apply();

        File file = new File(getSave_file_path, recordFileName + ".txt");

        try (FileOutputStream fos = new FileOutputStream(file);
             OutputStreamWriter osw = new OutputStreamWriter(fos);
             BufferedWriter bw = new BufferedWriter(osw)) {

            // 写入数据到文件
            bw.write("camera_par: " + result_string);
            bw.newLine();

        } catch (IOException e) {
            e.printStackTrace();
        }
        return result_string;
    }
    private void openCamera(int width, int height) {
        CameraManager manager = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
        try {
            cameraCharacteristics = manager.getCameraCharacteristics(cameraId);
            float maxZoom = cameraCharacteristics.get(CameraCharacteristics.SCALER_AVAILABLE_MAX_DIGITAL_ZOOM);
            Log.d(CAG, "maxZoom:" + maxZoom);
            StreamConfigurationMap map = cameraCharacteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
            mPreviewSize = chooseOptimalSize(map.getOutputSizes(SurfaceTexture.class), width, height);
            if ((checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) || (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED))  {
                Log.d(CAG, "No camera and storage permission");
                requestPermissions(new String[]{Manifest.permission.CAMERA, Manifest.permission.WRITE_EXTERNAL_STORAGE}, 1001);
            }
            Log.d(CAG, "开启相机");
            manager.openCamera(cameraId, mStateCallback,null);
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private void closeCamera() {
        try {
            mCameraOpenCloseLock.acquire();
            if (mCameraDevice != null) {
                mCameraDevice.close();
                mCameraDevice = null;
            }
            if (mCaptureSession != null) {
                mCaptureSession.close();
                mCaptureSession = null;
            }
        }catch (InterruptedException e) {
        throw new RuntimeException("Interrupted while trying to lock camera closing.");
    } finally {
        mCameraOpenCloseLock.release();
    }
        stopBackgroundThread();
    }

    private Size chooseOptimalSize(Size[] choices, int width, int height) {
        List<Size> bigEnough = new ArrayList<>();
        for (Size option : choices) {
            if (option.getWidth() >= width && option.getHeight() >= height) {
                bigEnough.add(option);
            }
        }
        if (bigEnough.size() > 0) {
            return Collections.min(bigEnough, new Comparator<Size>() {
                @Override
                public int compare(Size lhs, Size rhs) {
                    return Long.signum((long) lhs.getWidth() * lhs.getHeight() - (long) rhs.getWidth() * rhs.getHeight());
                }
            });
        } else {
            return choices[0];
        }
    }

    private void startBackgroundThread() {
        // 相机线程
        if (mCameraThread == null) {
            mCameraThread = new HandlerThread("CameraBackground");
            mCameraThread.start();
            mCameraHandler = new Handler(mCameraThread.getLooper());
        }
        // ImageReader线程
        if (mImageThread == null) {
            mImageThread = new HandlerThread("ImageBackground");
            mImageThread.start();
            mImageHandler = new Handler(mImageThread.getLooper());
        }

    }

    private void stopBackgroundThread() {
        if (mCameraThread != null) {
            mCameraThread.quitSafely();
            try {
                mCameraThread.join();
                mCameraThread = null;
                mCameraHandler = null;
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        if (mImageThread != null) {
            mImageThread.quitSafely();
            try {
                mImageThread.join();
                mImageThread = null;
                mImageHandler = null;
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }



    public native boolean detectYarnInImage(Bitmap inBitmap, Bitmap outBitmap, int[] roi1, int[] roi2, float[] det_par, String save_file_path, int yarnRow);
    public native void drawRoiRange(Bitmap inBitmap, Bitmap outBitmap, int[] roi1, int[] roi2);
    private static class ListItem {
        UsbDevice device;
        int port;
        UsbSerialDriver driver;

        ListItem(UsbDevice device, int port, UsbSerialDriver driver) {
            this.device = device;
            this.port = port;
            this.driver = driver;
        }
    }
    private void serialRefresh() {
        usbManager = (UsbManager) getSystemService(Context.USB_SERVICE);
        UsbSerialProber usbDefaultProber = UsbSerialProber.getDefaultProber();
        listItems.clear();
        for(UsbDevice device : usbManager.getDeviceList().values()) {
            UsbSerialDriver driver = usbDefaultProber.probeDevice(device);
            if(driver != null) {
                for(int port = 0; port < driver.getPorts().size(); port++)
                    listItems.add(new ListItem(device, port, driver));
            } else {
                listItems.add(new ListItem(device, 0, null));
            }
        }
        listAdapter.notifyDataSetChanged();
    }
    private void serialSendData(String msg){
        if (!serialOpenFlag || usbSerialPort == null){
            Toast.makeText(MainActivity.this, "No Select device", Toast.LENGTH_SHORT).show();
        }else {
            byte[] data = (msg + '\n').getBytes();
            try {
                usbSerialPort.write(data, WRITE_WAIT_MILLIS);
                Toast.makeText(MainActivity.this, "Send msg success!", Toast.LENGTH_SHORT).show();
            }catch (IOException e) {
                e.printStackTrace();
            }
        }
    }
    private void serialOpen(){
        if (serialOpenFlag){
            Toast.makeText(MainActivity.this, "Serial port enabled!", Toast.LENGTH_SHORT).show();
            return;
        }
        if (device_select != null)
        {
            if (usbManager == null){
                usbManager = (UsbManager) getSystemService(Context.USB_SERVICE);
            }
            usbConnection = usbManager.openDevice(device_select.driver.getDevice());
            if(usbConnection == null) {
                Toast.makeText(MainActivity.this, "UsbConnection empty!", Toast.LENGTH_SHORT).show();
                int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_MUTABLE : 0;
                Intent intent = new Intent(INTENT_ACTION_GRANT_USB);
                intent.setPackage(MainActivity.this.getPackageName());
                PendingIntent usbPermissionIntent = PendingIntent.getBroadcast(MainActivity.this, 0, intent, flags);
                usbManager.requestPermission(device_select.driver.getDevice(), usbPermissionIntent);
                return;
            }
            usbSerialPort = device_select.driver.getPorts().get(device_select.port); // Most devices have just one port (port 0)
            try {
                usbSerialPort.open(usbConnection);
                usbSerialPort.setParameters(baudRate, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
//                button_serial.setTextColor(Color.YELLOW);
            }
            catch (IOException e) {
                Toast.makeText(MainActivity.this, "Device serial open failed!", Toast.LENGTH_SHORT).show();
                throw new RuntimeException(e);
            }
            serialStartReceive();
            Toast.makeText(MainActivity.this, "Device serial open success!", Toast.LENGTH_SHORT).show();
            serialOpenFlag = true;
            executeAction("");
        }else {
            Toast.makeText(MainActivity.this, "No Select device", Toast.LENGTH_SHORT).show();
        }
    }
    public void serialStartReceive(){
        if(usbSerialPort == null || !usbSerialPort.isOpen()){return;}
        usbIoManager = new SerialInputOutputManager(usbSerialPort, new SerialInputOutputManager.Listener() {

            @Override
            public void onNewData(byte[] data) {
                String rec_msg = new String(data);
                runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
//                                Toast.makeText(MainActivity.this, "Serial rec data" + rec_msg, Toast.LENGTH_SHORT).show();
                                executeAction(rec_msg);
                            }
                        });
            }
            @Override
            public void onRunError(Exception e) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Log.e(IAG, "usb 断开了" );
                        Toast.makeText(MainActivity.this, "Serial rec error", Toast.LENGTH_SHORT).show();
                        serialDisconnect();
                        e.printStackTrace();
                    }
                });

            }
        });
        usbIoManager.setReadBufferSize(8192);
        usbIoManager.start();
    }
    private void serialDisconnect() {
        currentState = serialState.CLOSE;
        if(usbIoManager != null) {
            usbIoManager.setListener(null);
            usbIoManager.stop();
        }
        usbIoManager = null;
        try {
            usbSerialPort.close();
        } catch (IOException ignored) {
            ignored.printStackTrace();
        }
        usbSerialPort = null;
        button_serial.setTextColor(Color.BLACK);
        serialOpenFlag = false;
    }
    public void transitionToNextState() {
        serialState preState = currentState;
        int state_color = Color.BLACK;
        switch (currentState) {
            case CLOSE:
                currentState = serialState.OPEN;
                state_color = Color.YELLOW;
                break;
            case OPEN:
                currentState = serialState.ACTIVE;
                state_color = Color.BLUE;
                break;
            case ACTIVE:
                currentState = serialState.EDIT;
                state_color = Color.GREEN;
                break;
            case EDIT:
                currentState = serialState.ACTIVE;
                state_color = Color.BLUE;
                break;
        }
        int finalState_color = state_color;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(MainActivity.this, "State trans: " + preState + " to " + currentState, Toast.LENGTH_SHORT);
                button_serial.setTextColor(finalState_color);
            }
        });
    }

    public void executeAction(String rec_msg) {
        String[] rec_arr =  rec_msg.split(":");
        int rec_arr_len = rec_arr.length;
        if (rec_arr[0].equals("GS") & serialOpenFlag){
            serialSendData("Now State is " + currentState);
        }
        switch (currentState) {
            case CLOSE:
                transitionToNextState();
                break;
            case OPEN:
                if (rec_arr_len == 2 & rec_arr[0].equals("AC") & serialOpenFlag) {
                    serialSendData("Serial trans to Activity State!");
                    transitionToNextState();
                } else {
                    if (serialOpenFlag) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                tv_rec.append(rec_msg + "\n");
                            }
                        });
                    }
                }
                break;
            case ACTIVE:
                if (rec_arr_len == 2 & serialOpenFlag) {
                    if (rec_arr[0].equals("YR")) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                tv_machine_row.setText(rec_arr[1]);
                            }
                        });
                    } else if (rec_arr[0].equals("ED")) {
                        serialSendData("Serial trans to Edit State!");
                        transitionToNextState();
                    } else if (rec_arr[0].equals("RD")) {
                        if (roi_flag){
                            detect_flag = true;
                            serialSendData("Start detect");
                        }else {
                            serialSendData("Roi range not set");
                        }
                    } else if (rec_arr[0].equals("ST")) {
                        detect_flag = false;
                        serialSendData("Detect stop");
                    } else if (rec_arr[0].equals("PA")){
                        String msg_current_par = getMsgCurrentPar();
                        serialSendData(msg_current_par);
                    }
                    else if (rec_arr[0].equals("RC")) {
                        recordFlag = true;
                        serialSendData("Record Start");
                    } else if (rec_arr[0].equals("RS")){
                        recordFlag = false;
                        serialSendData("Record Stop");
                    }
                }else {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(MainActivity.this, "The serial port is receiving but cannot be resolved", Toast.LENGTH_SHORT).show();
                        }
                    });
                }
                break;
            case EDIT:
                if (rec_arr_len == 2 & serialOpenFlag) {
                    if (rec_arr[0].equals("BA")) {
                        serialSendData("Serial back to Activity State!");
                        transitionToNextState();
                    }
                    if (rec_arr[0].equals("RO")) {
//                        调节ROI区域
                        String[] rec_roi_arr = rec_arr[1].split(",");
                        if (rec_roi_arr.length != 8) {
                            serialSendData("Roi input length error!");
                        } else {
                            for (int j = 0; j < 8; j++) {
                                try {
                                    int temp = Integer.parseInt(rec_roi_arr[j]);
                                    if (j < 4) {
                                        if (j > 1) {
                                            arr_roi1[j] = temp + arr_roi1[j - 2];
                                        } else {
                                            arr_roi1[j] = temp;
                                        }
                                    } else {
                                        if (j > 5) {
                                            arr_roi2[j - 4] = temp + arr_roi2[j - 2 - 4];
                                        } else {
                                            arr_roi2[j - 4] = temp;
                                        }
                                    }
                                } catch (NumberFormatException e) {
                                    roi_flag = false;
                                    serialSendData("Roi input type error!");
                                    break;
                                }
                            }
                            String roi_msg_back = "roi_set: ";
                            for (int i = 0; i < 8; i++) {
                                roi_msg_back = roi_msg_back + rec_roi_arr[i] + " ";
                            }
                            serialSendData(roi_msg_back + "\n");
                            serialSendData(rec_msg + "\n");
                            roi_flag = true;
                        }
                    } else if (rec_arr[0].equals("CA")) {
//                        调节相机参数
                        String[] rec_camera_arr = rec_arr[1].split(",");
                        if (rec_camera_arr.length != 4) {
                            serialSendData("Camera input length error!");
                        } else {
                            try {
                                Long temp_camera_exposureTime = Long.parseLong(rec_camera_arr[0]);
                                int temp_camera_Iso = Integer.parseInt(rec_camera_arr[1]);
                                float temp_camera_focusDistance = Float.parseFloat(rec_camera_arr[2]);
                                float temp_camera_zoomRatio = Float.parseFloat(rec_camera_arr[3]);
                                if (myUtil.isCameraParametersValid(temp_camera_exposureTime, temp_camera_Iso, temp_camera_focusDistance, temp_camera_zoomRatio)){
                                    camera_exposureTime = temp_camera_exposureTime;
                                    camera_Iso = temp_camera_Iso;
                                    camera_focusDistance = temp_camera_focusDistance;
                                    camera_zoomRatio = temp_camera_zoomRatio;
                                }else {
                                    serialSendData("Camera input out of range!");
                                }
                                setCameraPar();
                                mCaptureSession.setRepeatingRequest(mPreviewBuilder.build(), mCaptureCallback, mCameraHandler);
                            } catch (NumberFormatException e) {
                                serialSendData("Camera input type error!");
                                break;
                            } catch (CameraAccessException e) {
                                throw new RuntimeException(e);
                            }
                        }
                    } else if (rec_arr[0].equals("DE")) {
                        String[] rec_detect_arr = rec_arr[1].split(",");
                        if (rec_detect_arr.length != 3) {
                            serialSendData("Detect input length error!");
                        }else {
                            for (int i = 0; i < 3; i++) {
                                detect_par_arr[i] = Float.parseFloat(rec_detect_arr[i]);
                            }
                        }
                    }  else if (rec_arr[0].equals("NA")) {
                        recordFileName = rec_arr[1];
                        if (myUtil.createFolder(getSave_file_path+"/"+recordFileName)) {
                            yarnRow = 0;
                            serialSendData("Set Record File Name:" + recordFileName);
                        }
                    } else if (rec_arr[0].equals("SA")) {
                        saveCameraPar();
                    } else {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(MainActivity.this, "The serial port is receiving but cannot be resolved", Toast.LENGTH_SHORT).show();
                            }
                        });
                    }
                }
                break;
        }
    }

    @NonNull
    private String getMsgCurrentPar() {
        String msg_current_par = "roi_range: ";
        for (int i = 0; i < 4; i++) {
            msg_current_par = msg_current_par + arr_roi1[i] + ",";
        }
        for (int i = 0; i < 4; i++) {
            msg_current_par = msg_current_par + arr_roi2[i] + ",";
        }
        msg_current_par = msg_current_par + "\n camera_par: E:" + camera_exposureTime + " ISO:" + camera_Iso + " focus:"+ camera_focusDistance;
        msg_current_par = msg_current_par + "\n detect_par: ";
        for (int i = 0; i < 3; i++) {
            msg_current_par = msg_current_par + detect_par_arr[i];
        }
        return msg_current_par;
    }
}

