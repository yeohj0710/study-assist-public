package kr.local.studyassist.publicapp;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ImageDecoder;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.SurfaceTexture;
import android.graphics.drawable.GradientDrawable;
import android.hardware.camera2.*;
import android.hardware.display.DisplayManager;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.hardware.camera2.params.MeteringRectangle;
import android.media.Image;
import android.media.ImageReader;
import android.os.*;
import android.text.InputType;
import android.text.SpannableString;
import android.text.style.ForegroundColorSpan;
import android.text.TextUtils;
import android.util.Log;
import android.util.LruCache;
import android.util.Size;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class StudyActivity extends Activity {
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService upload = Executors.newSingleThreadExecutor();
    private final ExecutorService poll = Executors.newSingleThreadExecutor();
    private final ExecutorService progressRequests = Executors.newSingleThreadExecutor();
    private final ExecutorService photoRequests = Executors.newSingleThreadExecutor();
    private final ExecutorService thumbnails = Executors.newFixedThreadPool(2);
    private final AtomicBoolean uploading = new AtomicBoolean();
    private final AtomicBoolean polling = new AtomicBoolean();
    private static final int INK = 0xffe1e8e4, GREEN = 0xff9cc3ae, PAPER = Color.BLACK;
    private static final int SURFACE = 0xff111614, ACTION = 0xff1e3329, MUTED = 0xff97a79f;
    private static final int EDGE = 0xff25302b, PULSE_IDLE = 0xff4d5d55, PULSE_BASE = 0xff2a3530;
    private static final int ACTION_PRESSED = 0xff274235, SURFACE_PRESSED = 0xff1a211e, CAPTION_SCRIM = 0xd9090c0b;
    private static final int PANEL_RADIUS = 12, CONTROL_RADIUS = 10, TILE_RADIUS = 8;
    private static final int MIN_STRENGTH = 30, MAX_STRENGTH = 255;
    private static final String[] SCREEN_DIRECTIONS = {
        "세로", "가슴 착용 가로", "반대 방향 가로", "세로 180도 뒤집기", "자동 회전"
    };
    private static final int[] SCREEN_ORIENTATIONS = {
        ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, ActivityInfo.SCREEN_ORIENTATION_REVERSE_LANDSCAPE,
        ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE, ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT,
        ActivityInfo.SCREEN_ORIENTATION_FULL_USER
    };
    private TextView status, runtime, lastAnswer;
    private HapticStrip hapticStrip;
    private LinearLayout toolbar, controlBar, statePanel, controls;
    private final Button[] directionButtons = new Button[3];
    private String cameraLabel;
    private Button action, screenButton;
    private View blackCover;
    private LinearLayout mainPage;
    private boolean blackScreen;
    private static final int[] REVEAL_KEYS = {
        KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN,
        KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN
    };
    private int revealStep;
    private long revealDeadline;
    private TextureView preview;
    private FrameLayout stage, cameraBox;
    private boolean landscape;
    private ProgressPanel progressPanel;
    private ReceivedPhotos receivedPhotos;
    private DisplayManager displayManager;
    private final DisplayManager.DisplayListener displayListener = new DisplayManager.DisplayListener() {
        @Override public void onDisplayAdded(int id) {}
        @Override public void onDisplayRemoved(int id) {}
        @Override public void onDisplayChanged(int id) {
            if (id == getWindowManager().getDefaultDisplay().getDisplayId()) placePreview();
        }
    };
    private SharedPreferences settings;
    private OrientationEventListener physicalOrientation;
    private volatile int deviceAngle;
    private HandlerThread thread;
    private Handler cameraHandler;
    private CameraDevice camera;
    private CameraCaptureSession capture;
    private CaptureRequest.Builder previewRequest;
    private ImageReader reader;
    private Surface previewSurface;
    private String cameraId;
    private int orientation;
    private Size previewSize;
    private boolean autofocus;
    private MeteringRectangle[] focusArea;
    private Rect focusSensor;
    private float focusX = -1f, focusY = -1f;
    private volatile int shotOrientation;
    private BatteryManager batteryManager;
    private PowerManager powerManager;
    private String powerRun;
    private long powerReportedAt;
    private boolean foreground;
    private boolean starting;
    private volatile boolean running;
    private boolean waitingForAnswers;
    private long lastPollSuccess;
    private volatile CaptureRun run;

    private static final class CaptureRun {
        final String id, address, secret, range;

        CaptureRun(String id, String address, String secret, String range) {
            this.id = id;
            this.address = address;
            this.secret = secret;
            this.range = range;
        }
    }
    private int sent, archived;
    private volatile int captureIntervalMs = 3000;
    private String lastFullRun;
    private byte[] lastFullSignature;
    private long lastFullAt;
    private volatile long watchMarksUntil;
    private String activePacket, ackPacket;
    private String activeAnswer;
    private boolean ackDone;
    private long activeVisit;
    private Runnable hapticEnd;
    private Vibrator vibration;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        settings = getSharedPreferences("study", MODE_PRIVATE);
        applyScreenOrientation();
        physicalOrientation = new OrientationEventListener(this) {
            @Override public void onOrientationChanged(int degrees) {
                if (degrees != ORIENTATION_UNKNOWN) deviceAngle = ((degrees + 45) / 90 * 90) % 360;
            }
        };
        vibration = getSystemService(Vibrator.class);
        batteryManager = getSystemService(BatteryManager.class);
        powerManager = getSystemService(PowerManager.class);
        displayManager = getSystemService(DisplayManager.class);
        getWindow().setStatusBarColor(PAPER);
        getWindow().setNavigationBarColor(PAPER);
        LinearLayout page = new LinearLayout(this);
        mainPage = page;
        landscape = getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        page.setOrientation(LinearLayout.VERTICAL);
        page.setGravity(Gravity.CENTER);
        page.setBackgroundColor(PAPER);
        page.setPadding(dp(16), dp(12), dp(16), dp(12));
        toolbar = new LinearLayout(this);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        TextView appTitle = label("학습 보조기", 19, INK, true);
        appTitle.setSingleLine(true);
        appTitle.setEllipsize(TextUtils.TruncateAt.END);
        toolbar.addView(appTitle, new LinearLayout.LayoutParams(0, -2, 1f));
        LinearLayout directions = new LinearLayout(this);
        directions.setPadding(dp(3), dp(2), dp(3), dp(2));
        directions.setBackground(background(SURFACE, CONTROL_RADIUS, EDGE));
        String[] choices = {"세로", "가로", "자동"};
        for (int i = 0; i < choices.length; i++) {
            int mode = i;
            Button option = button(choices[i], false);
            option.setPadding(dp(12), 0, dp(12), 0);
            option.setContentDescription(i == 2 ? "자동 회전" : choices[i] + " 고정");
            option.setOnClickListener(v -> chooseScreenDirection(mode));
            directionButtons[i] = option;
            directions.addView(option, new LinearLayout.LayoutParams(-2, dp(44)));
        }
        toolbar.addView(directions, new LinearLayout.LayoutParams(-2, -2));
        page.addView(toolbar, new LinearLayout.LayoutParams(-1, -2));
        updateDirectionButtons();
        stage = new FrameLayout(this);
        cameraBox = new FrameLayout(this);
        cameraBox.setBackground(background(SURFACE, PANEL_RADIUS, EDGE));
        cameraBox.setClipToOutline(true);
        preview = new TextureView(this);
        preview.setContentDescription("책 미리보기. 누르면 중앙에 초점을 맞춥니다.");
        preview.setOnClickListener(v -> refocus());
        cameraBox.addView(preview, new FrameLayout.LayoutParams(-1, -1));
        stage.addView(cameraBox, new FrameLayout.LayoutParams(
            dp(landscape ? 176 : 108), dp(landscape ? 132 : 144), Gravity.CENTER));
        progressPanel = new ProgressPanel();
        stage.addView(progressPanel, new FrameLayout.LayoutParams(dp(340), -1, Gravity.CENTER));
        LinearLayout.LayoutParams stageSpace = new LinearLayout.LayoutParams(-1, dp(landscape ? 144 : 192));
        stageSpace.bottomMargin = dp(14);
        page.addView(stage, stageSpace);
        controlBar = new LinearLayout(this);
        controlBar.setGravity(Gravity.CENTER_VERTICAL);
        statePanel = new LinearLayout(this);
        statePanel.setOrientation(LinearLayout.VERTICAL);
        status = label("촬영 준비", 15, INK, true);
        statePanel.addView(status, new LinearLayout.LayoutParams(-1, -2));
        runtime = label("", 13, MUTED, false);
        runtime.setVisibility(View.GONE);
        statePanel.addView(runtime, new LinearLayout.LayoutParams(-1, -2));
        lastAnswer = label("", 16, GREEN, true);
        statePanel.addView(lastAnswer, new LinearLayout.LayoutParams(-1, -2));
        showLastAnswer(savedLastAnswer());
        controlBar.addView(statePanel);
        controls = new LinearLayout(this);
        controls.setGravity(Gravity.CENTER);
        action = button("촬영 시작", true);
        action.setOnClickListener(v -> { if (running) stopCapture(); else start(); });
        controls.addView(action);
        Button photos = button("받은 사진", false);
        photos.setOnClickListener(v -> openPhotos());
        controls.addView(photos);
        Button settingsButton = button("설정", false);
        settingsButton.setOnClickListener(v -> configure());
        controls.addView(settingsButton);
        screenButton = button("화면 끄기", false);
        screenButton.setContentDescription("화면 끄기. 볼륨 올림, 내림, 올림, 내림으로 돌아옵니다.");
        screenButton.setOnClickListener(v -> setBlackScreen(true));
        screenButton.setVisibility(View.GONE);
        controls.addView(screenButton);
        controlBar.addView(controls);
        layoutControls();
        page.addView(controlBar, new LinearLayout.LayoutParams(-1, -2));
        hapticStrip = new HapticStrip();
        hapticStrip.restore(settings.getString("last_haptic_pattern", ""));
        LinearLayout.LayoutParams signalSpace = new LinearLayout.LayoutParams(-1, -2);
        signalSpace.topMargin = dp(6);
        page.addView(hapticStrip, signalSpace);
        FrameLayout root = new FrameLayout(this);
        root.addView(page, new FrameLayout.LayoutParams(-1, -1));
        blackCover = new View(this);
        blackCover.setBackgroundColor(Color.BLACK);
        blackCover.setVisibility(View.GONE);
        blackCover.setContentDescription("검은 화면입니다. 볼륨 올림, 내림, 올림, 내림을 4초 안에 누르면 돌아갑니다.");
        blackCover.setOnTouchListener((view, event) -> true);
        root.addView(blackCover, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        setCaptureLayout(false);
        preview.setSurfaceTextureListener(new TextureView.SurfaceTextureListener() {
            public void onSurfaceTextureAvailable(SurfaceTexture surface, int width, int height) { openCamera(); }
            public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int width, int height) { placePreview(); }
            public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) { return true; }
            public void onSurfaceTextureUpdated(SurfaceTexture surface) {}
        });
    }

    private int screenDirection() {
        int choice = settings.getInt("screen_direction", 1);
        return choice >= 0 && choice < SCREEN_DIRECTIONS.length ? choice : 1;
    }

    private void applyScreenOrientation() {
        int wanted = SCREEN_ORIENTATIONS[screenDirection()];
        if (getRequestedOrientation() != wanted) setRequestedOrientation(wanted);
    }

    private int directionMode(int choice) {
        if (choice == 4) return 2;
        return choice == 1 || choice == 2 ? 1 : 0;
    }

    private SharedPreferences.Editor saveScreenDirection(SharedPreferences.Editor edit, int choice) {
        int mode = directionMode(choice);
        if (mode != 2) edit.putInt(mode == 1 ? "landscape_direction" : "portrait_direction", choice);
        return edit.putInt("screen_direction", choice);
    }

    private void chooseScreenDirection(int mode) {
        int current = screenDirection();
        if (directionMode(current) == mode) return;
        SharedPreferences.Editor edit = saveScreenDirection(settings.edit(), current);
        int choice = mode == 2 ? 4 : mode == 1
            ? settings.getInt("landscape_direction", 1) : settings.getInt("portrait_direction", 0);
        saveScreenDirection(edit, choice).apply();
        updateDirectionButtons();
        applyScreenOrientation();
    }

    private void updateDirectionButtons() {
        int active = directionMode(screenDirection());
        for (int i = 0; i < directionButtons.length; i++) {
            Button option = directionButtons[i];
            boolean selected = i == active;
            option.setSelected(selected);
            option.setTextColor(selected ? INK : MUTED);
            option.setBackground(background(selected ? ACTION : SURFACE, CONTROL_RADIUS, selected ? GREEN : SURFACE));
        }
    }

    @Override public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        if (mainPage == null || hapticStrip == null) return;
        landscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE;
        layoutControls();
        hapticStrip.updateLegend();
        setCaptureLayout(running || waitingForAnswers);
        preview.post(this::placePreview);
        if (receivedPhotos != null) receivedPhotos.updateLayout();
    }

    private void layoutControls() {
        controlBar.setOrientation(landscape ? LinearLayout.HORIZONTAL : LinearLayout.VERTICAL);
        status.setGravity(Gravity.START);
        runtime.setGravity(landscape ? Gravity.START : Gravity.CENTER);
        lastAnswer.setGravity(landscape ? Gravity.START : Gravity.CENTER);
        LinearLayout.LayoutParams stateSpace = landscape
            ? new LinearLayout.LayoutParams(0, -2, 1f)
            : new LinearLayout.LayoutParams(-1, -2);
        if (landscape) stateSpace.setMarginEnd(dp(12));
        statePanel.setLayoutParams(stateSpace);
        LinearLayout.LayoutParams controlsSpace = new LinearLayout.LayoutParams(landscape ? -2 : -1, -2);
        if (!landscape) {
            controlsSpace.gravity = Gravity.CENTER_HORIZONTAL;
            controlsSpace.topMargin = dp(10);
        }
        controls.setLayoutParams(controlsSpace);
        for (int i = 0; i < controls.getChildCount(); i++) {
            Button child = (Button) controls.getChildAt(i);
            child.setPadding(dp(landscape ? 14 : 6), 0, dp(landscape ? 14 : 6), 0);
            LinearLayout.LayoutParams space = landscape
                ? new LinearLayout.LayoutParams(-2, dp(48))
                : new LinearLayout.LayoutParams(0, dp(48), 1f);
            if (i > 0) space.setMarginStart(dp(landscape ? 8 : 6));
            child.setLayoutParams(space);
        }
    }

    private GradientDrawable background(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }
    private GradientDrawable background(int color, int radius, int stroke) {
        GradientDrawable shape = background(color, radius);
        shape.setStroke(Math.max(1, dp(1)), stroke);
        return shape;
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView label(String text, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
        return view;
    }
    private Button button(String text, boolean primary) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextSize(13);
        button.setMaxLines(2);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setPadding(dp(14), 0, dp(14), 0);
        button.setStateListAnimator(null);
        button.setElevation(0);
        button.setTypeface(android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL));
        android.graphics.drawable.StateListDrawable states = new android.graphics.drawable.StateListDrawable();
        states.addState(new int[]{android.R.attr.state_pressed}, primary
            ? background(ACTION_PRESSED, CONTROL_RADIUS) : background(SURFACE_PRESSED, CONTROL_RADIUS, EDGE));
        states.addState(new int[]{android.R.attr.state_focused}, primary
            ? background(ACTION, CONTROL_RADIUS, GREEN) : background(SURFACE, CONTROL_RADIUS, GREEN));
        states.addState(new int[]{}, primary
            ? background(ACTION, CONTROL_RADIUS) : background(SURFACE, CONTROL_RADIUS, EDGE));
        button.setBackground(states);
        button.setTextColor(primary ? INK : GREEN);
        return button;
    }

    private void openPhotos() {
        String address = settings.getString("endpoint", "").replaceFirst("/$", "");
        String secret = settings.getString("key", "");
        if (!validEndpoint(address) || !secret.matches("[A-Za-z0-9_-]{24,120}")) {
            status.setText("설정에서 노트북 주소와 연결 키를 입력하세요");
            return;
        }
        receivedPhotos = new ReceivedPhotos(address, secret);
        receivedPhotos.show();
    }

    private final class ReceivedPhotos {
        private final String address, secret;
        private final ZoomPhoto image = new ZoomPhoto();
        private final GridView grid = new GridView(StudyActivity.this);
        private final LruCache<String, Bitmap> previews = new LruCache<>(30);
        private final Set<String> previewsInFlight = new HashSet<>();
        private final TextView info = label("", 13, INK, false);
        private final Button previous = button("더 오래된 사진", false);
        private final Button next = button("더 최근 사진", false);
        private final Button refresh = button("새로고침", false);
        private final Button overview = button("목록으로", false);
        private final Button retry = button("다시 열기", false);
        private List<String> names = Collections.emptyList();
        private String nextBefore;
        private boolean paging;
        private int position, generation;
        private boolean detail;
        private Dialog dialog;

        ReceivedPhotos(String address, String secret) {
            this.address = address;
            this.secret = secret;
        }

        void show() {
            LinearLayout content = new LinearLayout(StudyActivity.this);
            content.setOrientation(LinearLayout.VERTICAL);
            content.setPadding(dp(16), dp(8), dp(16), dp(12));
            content.setBackgroundColor(PAPER);
            LinearLayout header = new LinearLayout(StudyActivity.this);
            header.setGravity(Gravity.CENTER_VERTICAL);
            header.addView(label("받은 사진", 18, INK, true), new LinearLayout.LayoutParams(0, -2, 1));
            Button close = button("닫기", false);
            close.setOnClickListener(v -> dialog.dismiss());
            header.addView(close, new LinearLayout.LayoutParams(-2, dp(48)));
            content.addView(header, new LinearLayout.LayoutParams(-1, -2));
            image.setContentDescription("노트북이 받은 사진. 두 손가락으로 확대할 수 있습니다.");
            FrameLayout gallery = new FrameLayout(StudyActivity.this);
            grid.setHorizontalSpacing(dp(8));
            grid.setVerticalSpacing(dp(8));
            grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
            grid.setAdapter(new PhotoGrid());
            grid.setOnItemClickListener((parent, item, index, id) -> load(index));
            gallery.addView(grid, new FrameLayout.LayoutParams(-1, -1));
            gallery.addView(image, new FrameLayout.LayoutParams(-1, -1));
            LinearLayout.LayoutParams gallerySpace = new LinearLayout.LayoutParams(-1, 0, 1);
            gallerySpace.topMargin = dp(8);
            content.addView(gallery, gallerySpace);
            info.setGravity(Gravity.CENTER);
            info.setMinHeight(dp(40));
            content.addView(info);
            LinearLayout buttons = new LinearLayout(StudyActivity.this);
            for (Button button : Arrays.asList(overview, previous, next, refresh, retry)) {
                LinearLayout.LayoutParams space = new LinearLayout.LayoutParams(0, dp(48), 1);
                space.setMarginEnd(dp(4));
                buttons.addView(button, space);
            }
            content.addView(buttons);
            previous.setOnClickListener(v -> { if (detail) load(position + 1); else older(false); });
            image.swipe = delta -> load(position + delta);
            next.setOnClickListener(v -> load(position - 1));
            refresh.setOnClickListener(v -> list());
            overview.setOnClickListener(v -> showOverview());
            retry.setOnClickListener(v -> load(position));
            dialog = new Dialog(StudyActivity.this) {
                @Override public void onBackPressed() {
                    if (detail) showOverview();
                    else super.onBackPressed();
                }
            };
            dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
            dialog.setContentView(content);
            dialog.setOnDismissListener(ignored -> {
                if (receivedPhotos == this) receivedPhotos = null;
            });
            dialog.show();
            Window window = dialog.getWindow();
            if (window != null) window.setBackgroundDrawableResource(android.R.color.transparent);
            updateLayout();
            list();
        }

        void updateLayout() {
            grid.setNumColumns(landscape ? 3 : 2);
            Window window = dialog.getWindow();
            if (window != null) window.setLayout(Math.min(dp(664), getResources().getDisplayMetrics().widthPixels - dp(24)), -1);
        }

        private void controls(boolean busy) {
            previous.setVisibility(detail || nextBefore != null ? View.VISIBLE : View.GONE);
            next.setVisibility(detail ? View.VISIBLE : View.GONE);
            overview.setVisibility(detail ? View.VISIBLE : View.GONE);
            refresh.setVisibility(detail ? View.GONE : View.VISIBLE);
            retry.setVisibility(View.GONE);
            previous.setEnabled(!busy && (nextBefore != null || (detail && position + 1 < names.size())));
            next.setEnabled(!busy && position > 0);
            refresh.setEnabled(!busy);
            previous.setAlpha(previous.isEnabled() ? 1f : .5f);
            next.setAlpha(next.isEnabled() ? 1f : .5f);
        }

        private void list() {
            showOverview();
            int request = generation;
            controls(true);
            info.setText("사진 목록을 불러오는 중");
            photoRequests.execute(() -> {
                try {
                    JSONObject payload = photoPage(null);
                    List<String> received = photoNames(payload);
                    ui.post(() -> {
                        if (!dialog.isShowing() || request != generation) return;
                        names = received;
                        nextBefore = pageCursor(payload);
                        ((BaseAdapter) grid.getAdapter()).notifyDataSetChanged();
                        showOverview();
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        if (!dialog.isShowing() || request != generation) return;
                        info.setText("사진 목록을 불러오지 못했습니다. 노트북 연결을 확인하세요.");
                        controls(false);
                    });
                }
            });
        }

        private void showOverview() {
            boolean fromDetail = detail;
            generation++;
            detail = false;
            image.display(null);
            image.setVisibility(View.GONE);
            grid.setVisibility(View.VISIBLE);
            if (fromDetail) grid.setSelection(position);
            info.setText(names.isEmpty() ? "보관한 사진이 여기에 표시돼요" : "사진 " + names.size() + "장");
            controls(false);
        }

        private JSONObject photoPage(String cursor) throws Exception {
            String path = cursor == null ? "/photos" : "/photos?before=" + cursor;
            return new JSONObject(new String(fetch(path), StandardCharsets.UTF_8));
        }

        private String pageCursor(JSONObject payload) {
            String cursor = payload.optString("next_before", "");
            return cursor.matches("[0-9]{8}_[0-9]{6}_[0-9]{6}_[0-9a-f]{32}\\.jpg") ? cursor : null;
        }

        private List<String> photoNames(JSONObject payload) throws Exception {
            JSONArray values = payload.getJSONArray("photos");
            List<String> result = new ArrayList<>();
            for (int index = 0; index < values.length(); index++) {
                String name = values.getString(index);
                if (name.matches("[0-9]{8}_[0-9]{6}_[0-9]{6}_[0-9a-f]{32}\\.jpg")) result.add(name);
            }
            return result;
        }

        private void older(boolean openPhoto) {
            if (paging || nextBefore == null) return;
            paging = true;
            int request = generation;
            String cursor = nextBefore;
            controls(true);
            photoRequests.execute(() -> {
                try {
                    JSONObject payload = photoPage(cursor);
                    List<String> page = photoNames(payload);
                    ui.post(() -> {
                        paging = false;
                        if (!dialog.isShowing() || request != generation) return;
                        int firstOlder = names.size();
                        List<String> all = new ArrayList<>(names);
                        all.addAll(page);
                        names = all;
                        nextBefore = pageCursor(payload);
                        ((BaseAdapter) grid.getAdapter()).notifyDataSetChanged();
                        if (openPhoto && !page.isEmpty()) load(firstOlder);
                        else if (detail) controls(false);
                        else {
                            showOverview();
                            grid.setSelection(firstOlder);
                        }
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        paging = false;
                        if (!dialog.isShowing() || request != generation) return;
                        info.setText("이전 사진을 불러오지 못했습니다");
                        controls(false);
                    });
                }
            });
        }

        private void load(int index) {
            if (index == names.size()) { older(true); return; }
            if (index < 0 || index >= names.size()) return;
            int request = ++generation;
            detail = true;
            grid.setVisibility(View.GONE);
            image.setVisibility(View.VISIBLE);
            position = index;
            String name = names.get(index);
            controls(true);
            image.display(null);
            info.setText("사진을 불러오는 중");
            photoRequests.execute(() -> {
                try {
                    byte[] jpeg = fetch("/photos/" + name);
                    Bitmap bitmap = ImageDecoder.decodeBitmap(ImageDecoder.createSource(ByteBuffer.wrap(jpeg)),
                        (decoder, header, source) -> {
                            Size size = header.getSize();
                            float scale = Math.min(1f, 2400f / Math.max(size.getWidth(), size.getHeight()));
                            decoder.setTargetSize(Math.max(1, Math.round(size.getWidth() * scale)),
                                Math.max(1, Math.round(size.getHeight() * scale)));
                        });
                    ui.post(() -> {
                        if (!dialog.isShowing() || !detail || request != generation) return;
                        image.display(bitmap);
                        info.setText((position + 1) + " / " + names.size() + "장   " + photoTime(name) + "   좌우로 넘기기");
                        controls(false);
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        if (!dialog.isShowing() || !detail || request != generation) return;
                        info.setText("사진을 열지 못했습니다");
                        controls(false);
                        retry.setVisibility(View.VISIBLE);
                    });
                }
            });
        }

        private String photoTime(String name) {
            return name.substring(4, 6) + "/" + name.substring(6, 8) + " " + name.substring(9, 11) + ":"
                + name.substring(11, 13) + ":" + name.substring(13, 15);
        }

        private final class PhotoGrid extends BaseAdapter {
            public int getCount() { return names.size(); }
            public String getItem(int index) { return names.get(index); }
            public long getItemId(int index) { return index; }

            public View getView(int index, View reused, ViewGroup parent) {
                PhotoTile tile = reused instanceof PhotoTile ? (PhotoTile) reused : new PhotoTile();
                String name = getItem(index);
                String takenAt = photoTime(name);
                tile.setContentDescription("받은 사진 " + (index + 1) + ", " + takenAt);
                tile.time.setText(takenAt);
                tile.setTag(name);
                Bitmap cached = previews.get(name);
                tile.imageView.setImageBitmap(cached);
                if (cached == null && previewsInFlight.add(name)) thumbnails.execute(() -> {
                    Bitmap thumbnail = null;
                    try {
                        byte[] jpeg = fetch("/photos/" + name + "/thumbnail");
                        thumbnail = android.graphics.BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
                    } catch (java.io.IOException error) {
                        Log.w("StudyAssist", "사진 미리보기를 불러오지 못했습니다");
                    }
                    Bitmap bitmap = thumbnail;
                    ui.post(() -> {
                        previewsInFlight.remove(name);
                        if (bitmap == null || !dialog.isShowing()) return;
                        previews.put(name, bitmap);
                        View current = grid.findViewWithTag(name);
                        if (current instanceof PhotoTile) ((PhotoTile) current).imageView.setImageBitmap(bitmap);
                    });
                });
                return tile;
            }
        }

        private final class PhotoTile extends FrameLayout {
            final ImageView imageView = new ImageView(StudyActivity.this);
            final TextView time = label("", 12, INK, false);

            PhotoTile() {
                super(StudyActivity.this);
                setLayoutParams(new AbsListView.LayoutParams(-1, dp(136)));
                setBackground(background(SURFACE, TILE_RADIUS, EDGE));
                setClipToOutline(true);
                imageView.setScaleType(ImageView.ScaleType.CENTER_CROP);
                imageView.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
                addView(imageView, new FrameLayout.LayoutParams(-1, -1));
                time.setBackgroundColor(CAPTION_SCRIM);
                time.setPadding(dp(10), dp(5), dp(10), dp(5));
                time.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
                addView(time, new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM));
            }
        }

        private byte[] fetch(String path) throws java.io.IOException {
            HttpURLConnection connection = openRequest(address, secret, path, "GET", 6500);
            try {
                int size = connection.getContentLength();
                if (connection.getResponseCode() != 200 || size > 12 * 1024 * 1024) {
                    throw new java.io.IOException("Notebook could not return a photo");
                }
                try (InputStream in = connection.getInputStream()) { return in.readAllBytes(); }
            } finally {
                connection.disconnect();
            }
        }
    }

    private final class ZoomPhoto extends ImageView {
        private final Matrix transform = new Matrix();
        private float scale = 1, x, y, downX, downY;
        private boolean usedPinch;
        private java.util.function.IntConsumer swipe;
        private final ScaleGestureDetector pinch = new ScaleGestureDetector(StudyActivity.this,
            new ScaleGestureDetector.SimpleOnScaleGestureListener() {
                @Override public boolean onScale(ScaleGestureDetector detector) {
                    float target = Math.max(1f, Math.min(5f, scale * detector.getScaleFactor()));
                    transform.postScale(target / scale, target / scale, detector.getFocusX(), detector.getFocusY());
                    scale = target;
                    if (scale == 1f) fit();
                    else setImageMatrix(transform);
                    return true;
                }
            });

        ZoomPhoto() {
            super(StudyActivity.this);
            setScaleType(ScaleType.MATRIX);
        }

        void display(Bitmap bitmap) {
            setImageBitmap(bitmap);
            fit();
        }

        private void fit() {
            transform.reset();
            scale = 1f;
            if (getDrawable() == null || getWidth() == 0 || getHeight() == 0) return;
            int width = getDrawable().getIntrinsicWidth(), height = getDrawable().getIntrinsicHeight();
            float ratio = Math.min((float) getWidth() / width, (float) getHeight() / height);
            transform.setScale(ratio, ratio);
            transform.postTranslate((getWidth() - width * ratio) / 2, (getHeight() - height * ratio) / 2);
            setImageMatrix(transform);
        }

        @Override protected void onSizeChanged(int w, int h, int oldw, int oldh) {
            super.onSizeChanged(w, h, oldw, oldh);
            fit();
        }

        @Override public boolean onTouchEvent(MotionEvent event) {
            if (getDrawable() == null) return false;
            int action = event.getActionMasked();
            if (action == MotionEvent.ACTION_DOWN) {
                downX = event.getX();
                downY = event.getY();
                usedPinch = scale > 1f;
            }
            if (event.getPointerCount() > 1) usedPinch = true;
            pinch.onTouchEvent(event);
            if (action == MotionEvent.ACTION_UP && !usedPinch && swipe != null) {
                float dx = event.getX() - downX, dy = event.getY() - downY;
                if (Math.abs(dx) > dp(48) && Math.abs(dx) > 1.4f * Math.abs(dy)) swipe.accept(dx < 0 ? 1 : -1);
            }
            if (event.getActionMasked() == MotionEvent.ACTION_MOVE
                    && scale > 1f && !pinch.isInProgress() && event.getPointerCount() == 1) {
                transform.postTranslate(event.getX() - x, event.getY() - y);
                setImageMatrix(transform);
            }
            x = event.getX();
            y = event.getY();
            return true;
        }
    }

    private void configure() {
        LinearLayout fields = new LinearLayout(this);
        fields.setPadding(dp(22), dp(12), dp(22), dp(6));
        fields.setOrientation(LinearLayout.VERTICAL);
        addSettingsHeading(fields, "노트북 연결", 0);
        EditText address = new EditText(this), secret = new EditText(this);
        address.setSingleLine();
        address.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setHint("http:// 또는 https://");
        address.setText(settings.getString("endpoint", ""));
        secret.setSingleLine();
        secret.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        secret.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        secret.setHint("노트북의 연결 키를 붙여넣으세요");
        secret.setText(settings.getString("key", ""));
        addSettingField(fields, "노트북 주소", address);
        addSettingField(fields, "연결 키", secret);
        Button check = button("연결 확인", false);
        LinearLayout connectionRow = new LinearLayout(this);
        connectionRow.setGravity(Gravity.CENTER_VERTICAL);
        connectionRow.addView(check, new LinearLayout.LayoutParams(-2, dp(44)));
        Button models = button("모델 설정", false);
        models.setOnClickListener(v -> {
            if (checkConnectionFields(address, secret, true)) {
                new ModelPanel(connectionAddress(address), secret.getText().toString().trim()).show();
            }
        });
        LinearLayout.LayoutParams modelSpace = new LinearLayout.LayoutParams(-2, dp(44));
        modelSpace.setMarginStart(dp(6));
        connectionRow.addView(models, modelSpace);
        TextView feedback = label("", 13, MUTED, false);
        feedback.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        feedback.setVisibility(View.GONE);
        LinearLayout.LayoutParams feedbackSpace = new LinearLayout.LayoutParams(0, -2, 1f);
        feedbackSpace.setMarginStart(dp(10));
        connectionRow.addView(feedback, feedbackSpace);
        fields.addView(connectionRow, new LinearLayout.LayoutParams(-1, -2));
        TextView connectionHint = label("오프라인에서도 저장할 수 있어요.", 13, MUTED, false);
        connectionHint.setPadding(0, dp(6), 0, 0);
        fields.addView(connectionHint);
        addSettingsHeading(fields, "진동", 22);
        fields.addView(label("세기", 14, INK, false));
        SeekBar strength = new SeekBar(this);
        strength.setMax(MAX_STRENGTH - MIN_STRENGTH);
        strength.setProgress(vibrationStrength() - MIN_STRENGTH);
        fields.addView(strength);
        LinearLayout vibrationTests = new LinearLayout(this);
        Button contrast = button("짧게와 길게", false);
        contrast.setOnClickListener(v -> vibrate(new long[]{0, 140, 800, 620},
            strength.getProgress() + MIN_STRENGTH));
        vibrationTests.addView(contrast, new LinearLayout.LayoutParams(-2, dp(48)));
        Button test = button("17번 답 ③ 시험", false);
        test.setOnClickListener(v -> vibrate(new long[]{
            0, 140, 240, 140, 800, 140, 800, 620, 240, 140, 240, 140,
            1500, 140, 240, 140, 240, 140
        }, strength.getProgress() + MIN_STRENGTH));
        LinearLayout.LayoutParams testSpace = new LinearLayout.LayoutParams(-2, dp(48));
        testSpace.setMarginStart(dp(8));
        vibrationTests.addView(test, testSpace);
        fields.addView(vibrationTests);
        fields.addView(label("주머니에 넣은 상태에서 먼저 짧게와 길게를 비교해 보세요.", 13, MUTED, false));
        addSettingsHeading(fields, "촬영과 화면", 22);
        fields.addView(label("화면 방향 상세", 14, INK, false));
        Spinner direction = new Spinner(this);
        ArrayAdapter<String> directionAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, SCREEN_DIRECTIONS);
        directionAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        direction.setAdapter(directionAdapter);
        direction.setSelection(screenDirection());
        fields.addView(direction, new LinearLayout.LayoutParams(-1, dp(48)));
        EditText questionRange = new EditText(this);
        questionRange.setSingleLine();
        questionRange.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        questionRange.setHint("예: 1-10, 비워 두면 사진 기준");
        questionRange.setText(settings.getString("question_range", ""));
        addSettingField(fields, "확인할 문항 범위", questionRange);
        fields.addView(label("문항 범위는 다음 촬영부터 적용돼요.", 13, MUTED, false));
        fields.addView(label("검은 화면에서 돌아오려면 4초 안에 볼륨 올림, 내림, 올림, 내림을 누르세요.", 13, MUTED, false));
        if (cameraLabel != null) fields.addView(label(cameraLabel, 12, MUTED, false));
        ScrollView scroll = new ScrollView(this);
        scroll.addView(fields);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("설정").setView(scroll)
            .setPositiveButton("저장", null).setNegativeButton("닫기", null).show();
        if (dialog.getWindow() != null) dialog.getWindow().setLayout(
            Math.min(dp(520), getResources().getDisplayMetrics().widthPixels - dp(28)), -2);
        if (dialog.getWindow() != null) {
            dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
        }
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                if (!checkConnectionFields(address, secret, false)) return;
                String notebook = connectionAddress(address);
                String token = secret.getText().toString().trim();
                boolean changedNotebook = !notebook.equals(settings.getString("endpoint", "").replaceFirst("/$", ""))
                    || !token.equals(settings.getString("key", ""));
                String span = questionRange.getText().toString().trim().replaceAll("\\s+", "").replace('~', '-');
                if (!span.isEmpty()) {
                    String[] ends = span.split("-", -1);
                    if (!span.matches("[1-9][0-9]{0,2}-[1-9][0-9]{0,2}")
                            || Integer.parseInt(ends[0]) > Integer.parseInt(ends[1])) {
                        questionRange.setError("시작 번호와 끝 번호를 입력하세요. 예: 1-10");
                        questionRange.requestFocus();
                        return;
                    }
                }
                SharedPreferences.Editor edit = settings.edit().putString("endpoint", notebook)
                    .putString("key", token)
                    .putString("question_range", span)
                    .putInt("strength", strength.getProgress() + MIN_STRENGTH)
                    .putBoolean("strength_range_updated", true);
                saveScreenDirection(edit, direction.getSelectedItemPosition());
                if (changedNotebook) edit.remove("pending_run").remove("pending_range");
                edit.apply();
                if (changedNotebook && (running || waitingForAnswers)) {
                    run = null;
                    stop("연결 설정을 저장했습니다. 촬영을 다시 시작하세요.");
                    ackPacket = null;
                } else {
                    if (running || waitingForAnswers) Toast.makeText(this, "설정을 저장했습니다", Toast.LENGTH_SHORT).show();
                    else status.setText("설정을 저장했습니다");
                    progressPanel.refresh();
                }
                dialog.dismiss();
                updateDirectionButtons();
                applyScreenOrientation();
        });
        check.setOnClickListener(v -> {
            if (!checkConnectionFields(address, secret, true)) return;
            String notebook = connectionAddress(address);
            String token = secret.getText().toString().trim();
            check.setEnabled(false);
            feedback.setVisibility(View.VISIBLE);
            feedback.setText("노트북에 연결하는 중");
            progressRequests.execute(() -> {
                String message;
                try {
                    HttpURLConnection connection = openRequest(notebook, token, "/logs", "GET", 3000);
                    try {
                        int code = connection.getResponseCode();
                        if (code == 200) message = "노트북에 연결했습니다";
                        else if (code == 401 || code == 403) message = "연결 키가 맞는지 확인하세요";
                        else message = "노트북 주소와 실행 중인 서버를 확인하세요";
                    } finally { connection.disconnect(); }
                } catch (java.io.IOException error) {
                    message = "노트북에 연결하지 못했습니다. Tailscale과 서버 상태를 확인하세요.";
                }
                String result = message;
                ui.post(() -> {
                    if (!dialog.isShowing()) return;
                    check.setEnabled(true);
                    boolean same = notebook.equals(connectionAddress(address)) && token.equals(secret.getText().toString().trim());
                    feedback.setText(same ? result : "주소나 키가 바뀌었습니다. 다시 확인하세요.");
                });
            });
        });
    }
    private final class ModelPanel {
        private final String[] labels = {"Luna 6", "Sol 6.1", "Terra 6.1"};
        private final String[] ids = {"gpt-6-luna", "gpt-6.1-sol", "gpt-6.1-terra"};
        private final String address, secret;
        private final Spinner route = new Spinner(StudyActivity.this);
        private final Spinner solve = new Spinner(StudyActivity.this);
        private final CheckBox parallel = new CheckBox(StudyActivity.this);
        private final TextView status = label("", 13, MUTED, false);
        private final List<Button> presets = new ArrayList<>();
        private AlertDialog dialog;
        private boolean loaded;

        ModelPanel(String address, String secret) {
            this.address = address;
            this.secret = secret;
        }

        void show() {
            LinearLayout fields = new LinearLayout(StudyActivity.this);
            fields.setOrientation(LinearLayout.VERTICAL);
            fields.setPadding(dp(20), dp(8), dp(20), dp(4));
            LinearLayout quick = new LinearLayout(StudyActivity.this);
            addPreset(quick, "빠르게", 0, 0);
            addPreset(quick, "균형", 0, 1);
            addPreset(quick, "정밀", 1, 1);
            status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
            status.setPadding(0, 0, 0, dp(8));
            fields.addView(status, new LinearLayout.LayoutParams(-1, -2));
            fields.addView(quick);
            LinearLayout selectors = new LinearLayout(StudyActivity.this);
            addModelSelector(selectors, "판별 모델", route);
            addModelSelector(selectors, "풀이 모델", solve);
            fields.addView(selectors);
            parallel.setText("밀리면 두 묶음 동시 판별");
            parallel.setTextColor(INK);
            fields.addView(parallel);
            AdapterView.OnItemSelectedListener selection = new AdapterView.OnItemSelectedListener() {
                @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    updatePresets();
                }

                @Override public void onNothingSelected(AdapterView<?> parent) {}
            };
            route.setOnItemSelectedListener(selection);
            solve.setOnItemSelectedListener(selection);
            ScrollView scroll = new ScrollView(StudyActivity.this);
            scroll.addView(fields);
            dialog = new AlertDialog.Builder(StudyActivity.this).setTitle("모델 설정").setView(scroll)
                .setPositiveButton("적용", null).setNegativeButton("닫기", null)
                .setNeutralButton("새로고침", null).show();
            if (dialog.getWindow() != null) dialog.getWindow().setLayout(
                Math.min(dp(520), getResources().getDisplayMetrics().widthPixels - dp(28)), -2);
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> fetch(true));
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> fetch(false));
            fetch(false);
        }

        private void addPreset(LinearLayout row, String text, int judge, int answer) {
            Button preset = button(text, false);
            preset.setOnClickListener(v -> {
                route.setSelection(judge);
                solve.setSelection(answer);
                status.setText("적용을 누르면 노트북에 저장돼요.");
            });
            LinearLayout.LayoutParams space = new LinearLayout.LayoutParams(0, dp(44), 1f);
            if (!presets.isEmpty()) space.setMarginStart(dp(6));
            row.addView(preset, space);
            presets.add(preset);
        }

        private void addModelSelector(LinearLayout row, String title, Spinner spinner) {
            LinearLayout fields = new LinearLayout(StudyActivity.this);
            fields.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams column = new LinearLayout.LayoutParams(0, -2, 1f);
            if (row.getChildCount() > 0) column.setMarginStart(dp(10));
            row.addView(fields, column);
            TextView heading = label(title, 14, INK, true);
            heading.setPadding(0, dp(10), 0, 0);
            fields.addView(heading);
            spinner.setId(View.generateViewId());
            heading.setLabelFor(spinner.getId());
            ArrayAdapter<String> adapter = new ArrayAdapter<>(
                StudyActivity.this, android.R.layout.simple_spinner_item, labels);
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
            spinner.setAdapter(adapter);
            fields.addView(spinner, new LinearLayout.LayoutParams(-1, dp(42)));
        }

        private void updatePresets() {
            int selectedRoute = route.getSelectedItemPosition();
            int selectedSolve = solve.getSelectedItemPosition();
            int selected = selectedRoute == 0 && selectedSolve >= 0 && selectedSolve <= 1 ? selectedSolve
                : selectedRoute == 1 && selectedSolve == 1 ? 2 : -1;
            for (int i = 0; i < presets.size(); i++) {
                Button preset = presets.get(i);
                boolean active = loaded && i == selected;
                preset.setSelected(active);
                preset.setBackground(background(active ? ACTION : SURFACE, CONTROL_RADIUS, active ? GREEN : EDGE));
                preset.setTextColor(active ? INK : MUTED);
            }
        }

        private void setBusy(boolean busy) {
            boolean editable = !busy && loaded;
            route.setEnabled(editable);
            solve.setEnabled(editable);
            parallel.setEnabled(editable);
            for (Button preset : presets) preset.setEnabled(editable);
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(editable);
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setEnabled(!busy);
            updatePresets();
        }

        private void fetch(boolean save) {
            if (!save) loaded = false;
            setBusy(true);
            status.setText(save ? "노트북에 저장하는 중" : "노트북에서 모델 설정을 불러오는 중");
            String judge = save ? ids[route.getSelectedItemPosition()] : null;
            String answer = save ? ids[solve.getSelectedItemPosition()] : null;
            boolean boost = parallel.isChecked();
            progressRequests.execute(() -> {
                try {
                    JSONObject payload = save
                        ? new JSONObject().put("route", judge).put("solve", answer).put("parallel", boost) : null;
                    JSONObject current = requestModels(address, secret, payload);
                    int judgeIndex = Arrays.asList(ids).indexOf(current.getString("route"));
                    int answerIndex = Arrays.asList(ids).indexOf(current.getString("solve"));
                    boolean parallelEnabled = current.getBoolean("parallel");
                    if (judgeIndex < 0 || answerIndex < 0) throw new java.io.IOException("노트북 모델 설정을 읽을 수 없습니다.");
                    ui.post(() -> {
                        if (!dialog.isShowing()) return;
                        route.setSelection(judgeIndex);
                        solve.setSelection(answerIndex);
                        parallel.setChecked(parallelEnabled);
                        loaded = true;
                        setBusy(false);
                        status.setText(save ? "저장했어요. 다음 모델 호출부터 적용됩니다." : "노트북에서 사용 중인 설정이에요.");
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        if (!dialog.isShowing()) return;
                        setBusy(false);
                        status.setText(error instanceof ModelSettingError ? error.getMessage()
                            : save ? "모델 설정을 저장하지 못했어요. 연결을 확인하고 다시 적용하세요."
                                   : "모델 설정을 불러오지 못했어요. 연결을 확인하고 새로고침하세요.");
                    });
                }
            });
        }
    }

    private static final class ModelSettingError extends java.io.IOException {
        ModelSettingError(String message) { super(message); }
    }

    private JSONObject requestModels(String address, String secret, JSONObject payload) throws Exception {
        HttpURLConnection connection = openRequest(address, secret, "/models", payload == null ? "GET" : "POST", 3500);
        try {
            if (payload != null) {
                byte[] json = payload.toString().getBytes(StandardCharsets.UTF_8);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setFixedLengthStreamingMode(json.length);
                connection.setDoOutput(true);
                try (java.io.OutputStream out = connection.getOutputStream()) { out.write(json); }
            }
            int response = connection.getResponseCode();
            if (response == 401 || response == 403) throw new ModelSettingError("연결 키가 맞는지 확인하세요.");
            if (response == 404) throw new ModelSettingError("이 노트북에서 모델 설정을 열 수 없어요. 서버 버전을 확인하세요.");
            if (response != 200) throw new java.io.IOException("Cannot read notebook model settings");
            try (InputStream in = connection.getInputStream()) {
                return new JSONObject(new String(in.readAllBytes(), StandardCharsets.UTF_8));
            }
        } finally {
            connection.disconnect();
        }
    }

    private void addSettingsHeading(LinearLayout fields, String name, int topMargin) {
        TextView heading = label(name, 17, INK, true);
        LinearLayout.LayoutParams space = new LinearLayout.LayoutParams(-1, -2);
        space.topMargin = dp(topMargin);
        space.bottomMargin = dp(8);
        fields.addView(heading, space);
    }

    private void addSettingField(LinearLayout fields, String name, EditText input) {
        TextView title = label(name, 13, MUTED, true);
        input.setId(View.generateViewId());
        title.setLabelFor(input.getId());
        fields.addView(title, new LinearLayout.LayoutParams(-1, -2));
        input.setTextSize(15);
        input.setTextColor(INK);
        input.setHintTextColor(MUTED);
        input.setPadding(dp(12), dp(8), dp(12), dp(8));
        android.graphics.drawable.StateListDrawable border = new android.graphics.drawable.StateListDrawable();
        border.addState(new int[]{android.R.attr.state_focused}, background(SURFACE, CONTROL_RADIUS, GREEN));
        border.addState(new int[]{}, background(SURFACE, CONTROL_RADIUS, EDGE));
        input.setBackground(border);
        LinearLayout.LayoutParams space = new LinearLayout.LayoutParams(-1, dp(44));
        space.topMargin = dp(4);
        space.bottomMargin = dp(8);
        fields.addView(input, space);
    }
    private String connectionAddress(EditText address) {
        return address.getText().toString().trim().replaceFirst("/$", "");
    }

    private boolean checkConnectionFields(EditText address, EditText secret, boolean required) {
        String notebook = connectionAddress(address);
        String token = secret.getText().toString().trim();
        if ((required || !notebook.isEmpty()) && !validEndpoint(notebook)) {
            address.setError("https:// 또는 노트북 Tailscale 주소를 입력하세요");
            address.requestFocus();
            return false;
        }
        if ((required || !token.isEmpty()) && !token.matches("[A-Za-z0-9_-]{24,120}")) {
            secret.setError("노트북의 연결 키를 다시 붙여넣으세요");
            secret.requestFocus();
            return false;
        }
        return true;
    }
    private boolean validEndpoint(String endpoint) {
        try {
            URL url = new URL(endpoint);
            if (url.getUserInfo() != null || url.getQuery() != null || url.getRef() != null
                || !(url.getPath().isEmpty() || "/".equals(url.getPath()))) return false;
            if ("https".equals(url.getProtocol())) return true;
            if (!"http".equals(url.getProtocol())) return false;
            if ("127.0.0.1".equals(url.getHost())) return true;
            if (!url.getHost().matches("100\\.[0-9]{1,3}(\\.[0-9]{1,3}){2}")) return false;
            int segment = Integer.parseInt(url.getHost().split("\\.")[1]);
            return segment >= 64 && segment <= 127;
        } catch (Exception e) { return false; }
    }

    @Override public void onResume() {
        super.onResume();
        if (physicalOrientation.canDetectOrientation()) physicalOrientation.enable();
        foreground = true;
        if (displayManager != null) displayManager.registerDisplayListener(displayListener, ui);
        thread = new HandlerThread("StudyCamera");
        thread.start();
        cameraHandler = new Handler(thread.getLooper());
        openCamera();
        progressPanel.refresh();
        resumePendingAnswers();
    }
    private void resumePendingAnswers() {
        String previous = settings.getString("pending_run", "");
        if (previous.isEmpty()) return;
        String endpoint = settings.getString("endpoint", "").replaceFirst("/$", "");
        String key = settings.getString("key", "");
        if (!validEndpoint(endpoint) || !key.matches("[A-Za-z0-9_-]{24,120}")) return;
        run = new CaptureRun(previous, endpoint, key, settings.getString("pending_range", ""));
        waitingForAnswers = true;
        lastPollSuccess = SystemClock.elapsedRealtime();
        status.setText("촬영 중지, 남은 답 확인 중");
        syncControls();
        setCaptureLayout(true);
        ui.removeCallbacks(pollTick);
        ui.post(pollTick);
    }
    @Override public void onPause() {
        physicalOrientation.disable();
        if (displayManager != null) displayManager.unregisterDisplayListener(displayListener);
        foreground = false;
        if (running || waitingForAnswers) stop("촬영을 멈췄습니다");
        closeCamera();
        if (thread != null) thread.quitSafely();
        super.onPause();
    }
    @Override public void onDestroy() {
        upload.shutdownNow();
        poll.shutdownNow();
        progressRequests.shutdownNow();
        photoRequests.shutdownNow();
        thumbnails.shutdownNow();
        super.onDestroy();
    }
    @Override public void onRequestPermissionsResult(int request, String[] names, int[] choices) {
        super.onRequestPermissionsResult(request, names, choices);
        if (request == 4 && choices.length > 0 && choices[0] == PackageManager.PERMISSION_GRANTED) openCamera();
    }

    private void openCamera() {
        if (!foreground || !preview.isAvailable() || camera != null || starting) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            status.setText("카메라 권한을 허용하세요");
            return;
        }
        CameraManager manager = getSystemService(CameraManager.class);
        try {
            CameraCharacteristics selected = null;
            float field = 0f;
            for (String id : manager.getCameraIdList()) {
                CameraCharacteristics candidate = manager.getCameraCharacteristics(id);
                Integer facing = candidate.get(CameraCharacteristics.LENS_FACING);
                float[] focal = candidate.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS);
                android.util.SizeF sensor = candidate.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE);
                if (facing == null || facing != CameraCharacteristics.LENS_FACING_FRONT || focal == null
                    || focal.length != 1 || sensor == null) continue;
                if ("SM-S938N".equals(Build.MODEL) && (!"1".equals(id) || Math.abs(focal[0] - 3.3f) > .08f)) continue;
                float width = sensor.getWidth() / focal[0];
                if (width > field) {
                    field = width;
                    selected = candidate;
                    cameraId = id;
                }
            }
            if (selected == null) {
                status.setText("전면 카메라를 찾지 못했습니다");
                return;
            }
            orientation = Objects.requireNonNull(selected.get(CameraCharacteristics.SENSOR_ORIENTATION));
            int[] modes = selected.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES);
            autofocus = modes != null && Arrays.stream(modes).anyMatch(n -> n == CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
            Rect sensor = selected.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);
            Integer maxRegions = selected.get(CameraCharacteristics.CONTROL_MAX_REGIONS_AF);
            focusArea = null;
            focusX = focusY = -1f;
            focusSensor = autofocus && sensor != null && maxRegions != null && maxRegions > 0 ? sensor : null;
            setFocusArea(.52f, .72f, jpegOrientation());
            StreamConfigurationMap map = Objects.requireNonNull(selected.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP));
            Size jpeg = resolution(map.getOutputSizes(ImageFormat.JPEG), 4200);
            previewSize = resolution(map.getOutputSizes(SurfaceTexture.class), 1280);
            reader = ImageReader.newInstance(jpeg.getWidth(), jpeg.getHeight(), ImageFormat.JPEG, 2);
            reader.setOnImageAvailableListener(this::onImage, cameraHandler);
            float focal = selected.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)[0];
            cameraLabel = String.format(Locale.US, "전면 카메라 %.1fmm", focal);
            if ("카메라 권한을 허용하세요".contentEquals(status.getText())) status.setText("촬영 대기");
            Log.i("StudyAssist", "front camera selected id=" + cameraId + " focal=" + focal + " jpeg=" + jpeg
                  + " continuousAF=" + autofocus + " centralAF=" + (focusArea != null));
            starting = true;
            manager.openCamera(cameraId, new CameraDevice.StateCallback() {
                @Override public void onOpened(CameraDevice next) {
                    starting = false;
                    if (!foreground) { next.close(); return; }
                    camera = next;
                    startPreview(next);
                }
                @Override public void onDisconnected(CameraDevice next) { next.close(); cameraError("카메라 연결이 끊겼습니다"); }
                @Override public void onError(CameraDevice next, int error) {
                    next.close();
                    cameraError("전면 카메라를 열지 못했습니다 (" + error + ")");
                }
            }, ui);
        } catch (CameraAccessException | RuntimeException error) {
            cameraError("카메라를 여는 중 오류가 났습니다");
        }
    }
    private Size resolution(Size[] sizes, int limit) {
        return Arrays.stream(sizes).filter(s -> s.getWidth() <= limit && s.getWidth() * 3 == s.getHeight() * 4)
            .max(Comparator.comparingInt(Size::getWidth)).orElse(sizes[0]);
    }
    private void placePreview() {
        if (previewSize == null || preview.getWidth() == 0 || preview.getHeight() == 0) return;
        float w = preview.getWidth(), h = preview.getHeight();
        int displayDegrees = getWindowManager().getDefaultDisplay().getRotation() * 90;
        boolean sensorSwapped = orientation % 180 != 0;
        float sourceWidth = sensorSwapped ? previewSize.getHeight() : previewSize.getWidth();
        float sourceHeight = sensorSwapped ? previewSize.getWidth() : previewSize.getHeight();
        boolean displaySwapped = displayDegrees % 180 != 0;
        float rotatedWidth = displaySwapped ? sourceHeight : sourceWidth;
        float rotatedHeight = displaySwapped ? sourceWidth : sourceHeight;
        float fitScale = Math.min(w / rotatedWidth, h / rotatedHeight);
        Matrix fit = new Matrix();
        fit.setScale(fitScale * sourceWidth / w, fitScale * sourceHeight / h, w / 2, h / 2);
        fit.postRotate(-displayDegrees, w / 2, h / 2);
        preview.setTransform(fit);
    }
    private void startPreview(CameraDevice device) {
        try {
            SurfaceTexture texture = Objects.requireNonNull(preview.getSurfaceTexture());
            texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
            previewSurface = new Surface(texture);
            placePreview();
            device.createCaptureSession(Arrays.asList(previewSurface, reader.getSurface()), new CameraCaptureSession.StateCallback() {
                @Override public void onConfigured(CameraCaptureSession session) {
                    if (!foreground || camera != device) { session.close(); return; }
                    capture = session;
                    try {
                        previewRequest = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                        previewRequest.addTarget(previewSurface);
                        tune(previewRequest);
                        session.setRepeatingRequest(previewRequest.build(), null, cameraHandler);
                    } catch (CameraAccessException | IllegalStateException error) { cameraError("미리보기를 시작하지 못했습니다"); }
                }
                @Override public void onConfigureFailed(CameraCaptureSession session) { cameraError("전면 카메라 미리보기를 열지 못했습니다"); }
            }, ui);
        } catch (CameraAccessException | RuntimeException e) { cameraError("전면 카메라 구성을 열지 못했습니다"); }
    }
    private int jpegOrientation() { return (orientation - deviceAngle + 360) % 360; }

    private boolean setFocusArea(float x, float y, int rotation) {
        if (focusSensor == null || x < 0 || x > 1 || y < 0 || y > 1) return false;
        float sx = x, sy = y;
        if (rotation == 90) { sx = y; sy = 1f - x; }
        else if (rotation == 180) { sx = 1f - x; sy = 1f - y; }
        else if (rotation == 270) { sx = 1f - y; sy = x; }
        if (Math.abs(sx - focusX) + Math.abs(sy - focusY) < .08f) return false;
        focusX = sx;
        focusY = sy;
        int width = focusSensor.width() / 4, height = focusSensor.height() / 4;
        int left = Math.max(focusSensor.left, Math.min(focusSensor.right - width,
            focusSensor.left + Math.round(sx * focusSensor.width()) - width / 2));
        int top = Math.max(focusSensor.top, Math.min(focusSensor.bottom - height,
            focusSensor.top + Math.round(sy * focusSensor.height()) - height / 2));
        focusArea = new MeteringRectangle[]{new MeteringRectangle(left, top, width, height, MeteringRectangle.METERING_WEIGHT_MAX)};
        return true;
    }

    private void focusOnPage(JSONObject result, int rotation) {
        if (capture == null || previewRequest == null) return;
        if (!setFocusArea((float) result.optDouble("focus_x", -1), (float) result.optDouble("focus_y", -1), rotation)) return;
        try {
            tune(previewRequest);
            capture.setRepeatingRequest(previewRequest.build(), null, cameraHandler);
        } catch (CameraAccessException | IllegalStateException error) {
            Log.w("StudyAssist", "교재 초점 영역을 갱신하지 못했습니다");
        }
    }

    private void tune(CaptureRequest.Builder builder) {
        if (autofocus) builder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
        if (focusArea != null) builder.set(CaptureRequest.CONTROL_AF_REGIONS, focusArea);
        builder.set(CaptureRequest.FLASH_MODE, CaptureRequest.FLASH_MODE_OFF);
    }
    private void refocus() {
        if (!autofocus || capture == null || previewRequest == null) return;
        try {
            previewRequest.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_CANCEL);
            capture.capture(previewRequest.build(), null, cameraHandler);
            previewRequest.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_START);
            capture.capture(previewRequest.build(), new CameraCaptureSession.CaptureCallback() {
                @Override public void onCaptureCompleted(CameraCaptureSession session,
                        CaptureRequest request, TotalCaptureResult result) {
                    Log.i("StudyAssist", "Center focus trigger accepted, state=" + result.get(CaptureResult.CONTROL_AF_STATE));
                }
            }, cameraHandler);
            status.setText("교재에 초점을 다시 맞춥니다");
        } catch (CameraAccessException | IllegalStateException error) {
            status.setText("초점을 다시 맞추려면 앱을 다시 여세요");
        } finally {
            previewRequest.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_IDLE);
            try {
                capture.setRepeatingRequest(previewRequest.build(), null, cameraHandler);
            } catch (CameraAccessException | IllegalStateException error) {
                Log.w("StudyAssist", "Preview focus not resumed");
            }
        }
    }
    private void cameraError(String message) {
        stop(message);
        closeCamera();
        Log.w("StudyAssist", message);
    }
    private void closeCamera() {
        if (capture != null) capture.close();
        if (camera != null) camera.close();
        if (reader != null) reader.close();
        if (previewSurface != null) previewSurface.release();
        capture = null; camera = null; reader = null; previewSurface = null; previewRequest = null; starting = false;
    }
    private void start() {
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, 4);
            return;
        }
        if (capture == null) {
            status.setText("전면 미리보기가 열린 뒤 다시 누르세요");
            openCamera();
            return;
        }
        String endpoint = settings.getString("endpoint", "").replaceFirst("/$", "");
        String key = settings.getString("key", "");
        if (!validEndpoint(endpoint) || !key.matches("[A-Za-z0-9_-]{24,120}")) {
            status.setText("노트북 주소와 연결 키가 필요합니다");
            configure();
            return;
        }
        if (!waitingForAnswers) {
            run = new CaptureRun(UUID.randomUUID().toString(), endpoint, key, settings.getString("question_range", ""));
            settings.edit().putString("pending_run", run.id).putString("pending_range", run.range).apply();
            ackPacket = null;
            sent = 0;
            archived = 0;
            captureIntervalMs = 3000;
            watchMarksUntil = 0;
            runtime.setText("");
            runtime.setVisibility(View.GONE);
        }
        waitingForAnswers = false;
        running = true;
        status.setText("사진을 보내는 중");
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        syncControls();
        setCaptureLayout(true);
        progressPanel.refresh();
        ui.post(captureTick);
        ui.removeCallbacks(pollTick);
        ui.post(pollTick);
    }
    private void stopCapture() {
        running = false;
        setBlackScreen(false);
        waitingForAnswers = true;
        lastPollSuccess = SystemClock.elapsedRealtime();
        ui.removeCallbacks(captureTick);
        syncControls();
        status.setText("촬영 중지, 남은 답을 기다리는 중");
    }
    private void stop(String text) {
        running = false;
        if (!foreground) setBlackScreen(false);
        waitingForAnswers = false;
        ui.removeCallbacks(captureTick);
        ui.removeCallbacks(pollTick);
        finishHaptic(false);
        if (vibration != null) vibration.cancel();
        setCaptureLayout(false);
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        syncControls();
        status.setText(text);
        if (foreground) progressPanel.refresh();
    }
    private void syncControls() {
        action.setText(running ? "촬영 중지" : waitingForAnswers ? "촬영 계속" : "촬영 시작");
        boolean active = running || waitingForAnswers;
        screenButton.setVisibility(active ? View.VISIBLE : View.GONE);
    }
    private void setCaptureLayout(boolean capturing) {
        progressPanel.setCapturing(capturing);
        Configuration dimensions = getResources().getConfiguration();
        int available = Math.min(dp(landscape ? 636 : 420),
            getResources().getDisplayMetrics().widthPixels - dp(32));
        int gap = dp(12);
        int textAllowance = Math.max(0, Math.round((dimensions.fontScale - 1f) * 90));
        int stageHeight = landscape
            ? Math.min(170, Math.max(90, dimensions.screenHeightDp - 229 - textAllowance))
            : Math.min(382, Math.max(192, dimensions.screenHeightDp - 254 - textAllowance));
        int cameraWidth = landscape ? Math.min(dp(194), (available - gap) / 3) : available;
        int cameraHeight = landscape ? Math.min(dp(stageHeight), cameraWidth * 3 / 4)
            : dp(Math.min(174, stageHeight / 2));
        LinearLayout.LayoutParams toolbarSpace = (LinearLayout.LayoutParams) toolbar.getLayoutParams();
        toolbarSpace.width = available;
        toolbarSpace.bottomMargin = dp(landscape ? 8 : 12);
        toolbar.setLayoutParams(toolbarSpace);
        LinearLayout.LayoutParams stageSpace = (LinearLayout.LayoutParams) stage.getLayoutParams();
        stageSpace.height = dp(stageHeight);
        stageSpace.width = available;
        stageSpace.bottomMargin = dp(12);
        stage.setLayoutParams(stageSpace);
        FrameLayout.LayoutParams panel = (FrameLayout.LayoutParams) progressPanel.getLayoutParams();
        panel.width = landscape ? available - cameraWidth - gap : available;
        panel.height = landscape ? -1 : stageSpace.height - cameraHeight - gap;
        panel.gravity = landscape ? Gravity.END | Gravity.CENTER_VERTICAL : Gravity.BOTTOM;
        progressPanel.setLayoutParams(panel);
        FrameLayout.LayoutParams cameraSpace = (FrameLayout.LayoutParams) cameraBox.getLayoutParams();
        cameraSpace.width = cameraWidth;
        cameraSpace.height = cameraHeight;
        cameraSpace.gravity = landscape ? Gravity.START | Gravity.CENTER_VERTICAL : Gravity.TOP;
        cameraBox.setLayoutParams(cameraSpace);
        LinearLayout.LayoutParams barSpace = (LinearLayout.LayoutParams) controlBar.getLayoutParams();
        barSpace.width = available;
        controlBar.setLayoutParams(barSpace);
        LinearLayout.LayoutParams signalSpace = (LinearLayout.LayoutParams) hapticStrip.getLayoutParams();
        signalSpace.width = barSpace.width;
        hapticStrip.setLayoutParams(signalSpace);
    }
    private void setBlackScreen(boolean enabled) {
        if (enabled && !running && !waitingForAnswers) return;
        if (blackScreen == enabled) return;
        revealStep = 0;
        blackScreen = enabled;
        blackCover.setVisibility(enabled ? View.VISIBLE : View.GONE);
        hapticStrip.refresh();
        mainPage.setImportantForAccessibility(enabled ? View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS
            : View.IMPORTANT_FOR_ACCESSIBILITY_AUTO);
        Window window = getWindow();
        if (Build.VERSION.SDK_INT >= 30 && window.getInsetsController() != null) {
            WindowInsetsController bars = window.getInsetsController();
            if (enabled) {
                bars.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                bars.hide(WindowInsets.Type.systemBars());
            }
            else bars.show(WindowInsets.Type.systemBars());
        } else {
            window.getDecorView().setSystemUiVisibility(enabled
                ? View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                : 0);
        }
        WindowManager.LayoutParams params = window.getAttributes();
        params.screenBrightness = enabled ? WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_OFF
            : WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
        window.setAttributes(params);
    }
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        int key = event.getKeyCode();
        if (!blackScreen || (key != KeyEvent.KEYCODE_VOLUME_UP && key != KeyEvent.KEYCODE_VOLUME_DOWN)) {
            return super.dispatchKeyEvent(event);
        }
        if (event.getAction() != KeyEvent.ACTION_UP) return true;
        long now = event.getEventTime();
        if (event.isCanceled() || now - event.getDownTime() > 600) {
            revealStep = 0;
            return true;
        }
        if (now > revealDeadline || key != REVEAL_KEYS[revealStep]) revealStep = 0;
        if (key == REVEAL_KEYS[revealStep]) {
            if (revealStep == 0) revealDeadline = now + 4000;
            if (++revealStep == REVEAL_KEYS.length) setBlackScreen(false);
        }
        return true;
    }
    @Override public void onBackPressed() {
        if (!blackScreen) super.onBackPressed();
    }
    private String savedLastAnswer() {
        return settings.getString("last_answer", "").replaceFirst("^마지막 답 ", "마지막 전송 ");
    }

    private void showLastAnswer(String message) {
        lastAnswer.setText(message);
        lastAnswer.setVisibility(message.isEmpty() ? View.GONE : View.VISIBLE);
    }
    private final Runnable captureTick = new Runnable() {
        @Override public void run() {
            if (!running) return;
            if (!uploading.get() && camera != null && capture != null) {
                try {
                    CaptureRequest.Builder shot = camera.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
                    shot.addTarget(reader.getSurface());
                    tune(shot);
                    shotOrientation = jpegOrientation();
                    shot.set(CaptureRequest.JPEG_ORIENTATION, shotOrientation);
                    shot.set(CaptureRequest.JPEG_QUALITY, (byte) (captureIntervalMs == 6000 ? 90 : 95));
                    capture.capture(shot.build(), null, cameraHandler);
                } catch (CameraAccessException | IllegalStateException e) { cameraError("촬영이 멈췄습니다. 다시 시작하세요."); return; }
            }
            ui.postDelayed(this, effectiveCaptureInterval());
        }
    };
    private void onImage(ImageReader source) {
        CaptureRun current = run;
        byte[] jpeg;
        try (Image image = source.acquireLatestImage()) {
            if (image == null || !running || current == null || !uploading.compareAndSet(false, true)) return;
            ByteBuffer buffer = image.getPlanes()[0].getBuffer();
            jpeg = new byte[buffer.remaining()];
            buffer.get(jpeg);
        } catch (IllegalStateException ignored) { return; }
        int rotation = shotOrientation;
        upload.execute(() -> {
            try {
                if (current != run) return;
                byte[] signature = captureSignature(jpeg);
                long capturedAt = SystemClock.elapsedRealtime();
                long refreshAfter = capturedAt < watchMarksUntil ? 18000 : 60000;
                if (captureIntervalMs == 6000 && current.id.equals(lastFullRun)
                        && capturedAt - lastFullAt < refreshAfter && almostSame(signature, lastFullSignature)) {
                    try {
                        JSONObject heartbeat = request(current, "/still", null, null, false, false);
                        if (heartbeat.optBoolean("same")) return;
                    } catch (Exception error) {
                        Log.d("StudyAssist", "같은 장면 확인 실패, 원본 전송");
                    }
                }
                if (current != run) return;
                JSONObject result = request(current, "/frame", jpeg, null, false, false);
                lastFullRun = current.id;
                lastFullSignature = signature;
                lastFullAt = capturedAt;
                ui.post(() -> {
                    if ((!running && !waitingForAnswers) || current != run) return;
                    focusOnPage(result, rotation);
                    int interval = result.optInt("interval_ms", result.optBoolean("steady") ? 6000 : 3000);
                    captureIntervalMs = interval == 6000 ? 6000 : 3000;
                    sent++;
                    archived = Math.max(archived, result.optInt("archive_count", archived + (result.optBoolean("archived") ? 1 : 0)));
                    showCaptureCounts();
                    String step = result.optString("status", "사진을 받았습니다");
                    if (running) status.setText(step);
                    Log.i("StudyAssist", "사진 " + sent + "장 전송, " + step);
                });
            } catch (Exception error) {
                ui.post(() -> { if (running && current == run) status.setText("사진을 보내지 못했습니다. 설정에서 연결을 확인하세요."); });
            } finally { uploading.set(false); }
        });
    }
    private int thermalStatus() {
        return Build.VERSION.SDK_INT >= 29 && powerManager != null ? powerManager.getCurrentThermalStatus() : 0;
    }

    private int effectiveCaptureInterval() {
        int thermal = thermalStatus();
        if (thermal >= PowerManager.THERMAL_STATUS_CRITICAL) return Math.max(20000, captureIntervalMs);
        if (thermal >= PowerManager.THERMAL_STATUS_SEVERE) return Math.max(12000, captureIntervalMs);
        return captureIntervalMs;
    }

    private void showCaptureCounts() {
        int interval = effectiveCaptureInterval();
        runtime.setText("전송 " + sent + "장, 저장 " + archived + "장, " + interval / 1000 + "초 간격"
            + (interval > captureIntervalMs ? " / 발열로 촬영 간격 조절" : ""));
        runtime.setVisibility(View.VISIBLE);
    }
    private byte[] captureSignature(byte[] jpeg) {
        android.graphics.BitmapFactory.Options options = new android.graphics.BitmapFactory.Options();
        options.inSampleSize = 16;
        Bitmap sample = android.graphics.BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length, options);
        if (sample == null) return null;
        Bitmap small = Bitmap.createScaledBitmap(sample, 80, 60, true);
        int[] pixels = new int[80 * 60];
        small.getPixels(pixels, 0, 80, 0, 0, 80, 60);
        if (small != sample) small.recycle();
        sample.recycle();
        byte[] signature = new byte[pixels.length];
        for (int i = 0; i < pixels.length; i++) {
            int rgb = pixels[i];
            signature[i] = (byte) ((3 * ((rgb >> 16) & 255) + 6 * ((rgb >> 8) & 255) + (rgb & 255)) / 10);
        }
        return signature;
    }
    private boolean almostSame(byte[] current, byte[] previous) {
        if (current == null || previous == null) return false;
        int total = 0, changed = 0;
        for (int i = 0; i < current.length; i++) {
            int delta = Math.abs((current[i] & 255) - (previous[i] & 255));
            if (delta > 12 && ++changed > 18) return false;
            total += delta;
        }
        return total <= current.length * 2;
    }
    private final Runnable pollTick = new Runnable() {
        @Override public void run() {
            if (!running && !waitingForAnswers) return;
            if (polling.compareAndSet(false, true)) {
                CaptureRun current = run;
                String ack = ackPacket;
                boolean done = ackDone, draining = waitingForAnswers;
                poll.execute(() -> {
                    try {
                        if (current == null || current != run) return;
                        JSONObject result = request(current, "/poll", null, ack, done, draining);
                        ui.post(() -> {
                            if ((!running && !waitingForAnswers) || current != run) return;
                            lastPollSuccess = SystemClock.elapsedRealtime();
                            if (ack != null && ack.equals(ackPacket)) ackPacket = null;
                            progressPanel.acceptLive(result);
                            applyHaptic(result);
                            int archiveCount = result.optInt("archive_count", archived);
                            if (sent > 0 && archiveCount > archived) {
                                archived = archiveCount;
                                showCaptureCounts();
                            }
                            if (waitingForAnswers && draining && !result.optBoolean("waiting") && !uploading.get()) {
                                settings.edit().remove("pending_run").remove("pending_range").apply();
                                if (!result.optBoolean("valid")) stop("노트북에 이전 촬영 기록이 없습니다");
                                else if (result.optInt("review_needed") > 0) stop("다시 확인할 문항이 있습니다. 진행 기록을 보세요.");
                                else stop("촬영 중지, 남은 응답 확인 완료");
                            }
                        });
                    } catch (Exception error) {
                        ui.post(() -> {
                            if (current != run) return;
                            if (running) status.setText("노트북 응답이 없습니다. 설정에서 연결을 확인하세요.");
                            if (waitingForAnswers && SystemClock.elapsedRealtime() - lastPollSuccess >= 90000) {
                                stop("남은 답을 받지 못했습니다. 노트북 연결을 확인하세요.");
                            }
                        });
                    } finally { polling.set(false); }
                });
            }
            ui.postDelayed(this, activePacket != null || ackPacket != null ? 800 : 1400);
        }
    };
    private static final class ProgressEntry {
        final long id;
        final String text;

        ProgressEntry(long id, String text) {
            this.id = id;
            this.text = text;
        }
    }

    private static final class ProgressHistory {
        final List<ProgressEntry> entries = new ArrayList<>();
        private long firstAvailableId = 1;

        int indexOf(long id) {
            int low = 0, high = entries.size();
            while (low < high) {
                int mid = low + (high - low) / 2;
                if (entries.get(mid).id < id) low = mid + 1;
                else high = mid;
            }
            return low < entries.size() && entries.get(low).id == id ? low : -low - 1;
        }

        boolean merge(List<ProgressEntry> page, long before, boolean more) {
            if (!more) {
                long first = page.isEmpty() ? before : page.get(0).id;
                firstAvailableId = Math.max(firstAvailableId, first);
            }
            boolean changed = false;
            for (ProgressEntry entry : page) {
                int index = indexOf(entry.id);
                if (index < 0) {
                    entries.add(-index - 1, entry);
                    changed = true;
                }
            }
            return changed;
        }

        long cursorNear(int firstVisible) {
            for (int i = firstVisible; i < entries.size() && i <= firstVisible + 3; i++) {
                long id = entries.get(i).id;
                if (i == 0 ? id > firstAvailableId : id - entries.get(i - 1).id > 1) return id;
            }
            return 0;
        }
    }

    private final class ProgressPanel extends LinearLayout {
        private final ListView list = new ListView(StudyActivity.this);
        private final TextView title = label("진행 기록", 14, INK, true);
        private final Button jump = button("최신으로", false);
        private final Button clear = button("비우기", false);
        private final ProgressRows rows = new ProgressRows();
        private ProgressHistory history = new ProgressHistory();
        private List<ProgressEntry> fallback = new ArrayList<>();
        private String address, secret;
        private int connection;
        private boolean capturing, loading, refreshPending, scrolling, followNewest = true;
        private long retryAt, clearedThrough;
        private String emptyNotice = "";

        ProgressPanel() {
            super(StudyActivity.this);
            String notebook = settings.getString("endpoint", "").replaceFirst("/$", "");
            String cached = notebook.equals(settings.getString("last_progress_endpoint", notebook))
                ? settings.getString("last_progress", "") : "";
            String[] lines = cached.split("\n");
            for (int i = 1; i < lines.length; i++) fallback.add(new ProgressEntry(-2 - i, lines[i]));
            setOrientation(VERTICAL);
            setBackground(background(SURFACE, PANEL_RADIUS, EDGE));
            setClipToOutline(true);
            LinearLayout heading = new LinearLayout(StudyActivity.this);
            heading.setGravity(Gravity.CENTER_VERTICAL);
            heading.setPadding(dp(14), dp(2), dp(6), 0);
            heading.addView(title, new LinearLayout.LayoutParams(0, -2, 1f));
            jump.setVisibility(View.GONE);
            jump.setOnClickListener(v -> {
                followNewest = true;
                list.setSelection(rows.getCount() - 1);
            });
            heading.addView(jump, new LinearLayout.LayoutParams(-2, dp(44)));
            clear.setContentDescription("진행 기록 비우기");
            clear.setOnClickListener(v -> new AlertDialog.Builder(StudyActivity.this)
                .setTitle("진행 기록을 비울까요?")
                .setMessage("폰의 진행 기록을 비웁니다. 노트북에 연결돼 있으면 노트북의 기록도 비웁니다. 받은 사진과 진행 중인 풀이는 남습니다.")
                .setNegativeButton("취소", null)
                .setPositiveButton("비우기", (dialog, which) -> clearHistory()).show());
            heading.addView(clear, new LinearLayout.LayoutParams(-2, dp(44)));
            addView(heading, new LinearLayout.LayoutParams(-1, -2));
            list.setContentDescription("진행 기록");
            list.setDivider(null);
            list.setDividerHeight(0);
            list.setSelector(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
            list.setPadding(0, 0, 0, dp(8));
            list.setStackFromBottom(true);
            list.setAdapter(rows);
            addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
            list.setOnScrollListener(new AbsListView.OnScrollListener() {
                public void onScrollStateChanged(AbsListView view, int state) {
                    scrolling = state != SCROLL_STATE_IDLE;
                    updateFollowNewest(list.getFirstVisiblePosition(), list.getChildCount(), rows.getCount());
                }

                public void onScroll(AbsListView view, int first, int visible, int count) {
                    if (visible == 0 || count != rows.getCount()) return;
                    updateFollowNewest(first, visible, count);
                    if (!foreground || blackScreen || loading || SystemClock.elapsedRealtime() < retryAt) return;
                    long cursor = history.cursorNear(first);
                    if (cursor > 0) fetchPage(cursor);
                }
            });
        }

        private void clearHistory() {
            int current = ++connection;
            String notebook = address, token = secret;
            if (notebook != null && notebook.equals(settings.getString("last_progress_endpoint", ""))) {
                clearedThrough = Math.max(clearedThrough, settings.getLong("last_progress_id", 0));
            }
            boolean configured = validEndpoint(notebook) && token.matches("[A-Za-z0-9_-]{24,120}");
            emptyNotice = configured ? "폰 기록을 비웠습니다. 노트북에 연결하는 중" : "폰 기록을 비웠습니다. 노트북 연결은 설정에서 확인하세요.";
            resetPhoneHistory();
            refreshPending = false;
            loading = configured;
            if (!configured) return;
            clear.setEnabled(false);
            progressRequests.execute(() -> {
                try {
                    long last = requestProgress(notebook, token, "/logs/clear", "POST").getLong("cleared_through");
                    ui.post(() -> {
                        if (isDestroyed()) return;
                        clear.setEnabled(true);
                        if (current != connection) return;
                        clearedThrough = Math.max(clearedThrough, last);
                        emptyNotice = "폰과 노트북의 진행 기록을 비웠습니다";
                        resetPhoneHistory();
                        loading = false;
                        refresh();
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        if (isDestroyed()) return;
                        clear.setEnabled(true);
                        if (current != connection) return;
                        loading = false;
                        emptyNotice = "폰 기록을 비웠습니다. 노트북 기록은 연결한 뒤 비울 수 있습니다.";
                        rowsChanged();
                    });
                }
            });
        }

        private void resetPhoneHistory() {
            history = new ProgressHistory();
            fallback.clear();
            SharedPreferences.Editor edit = settings.edit().remove("last_progress")
                .remove("last_progress_id").remove("last_progress_endpoint");
            if (address != null) edit.putString("cleared_progress_endpoint", address).putLong("cleared_progress_through", clearedThrough);
            edit.apply();
            followNewest = true;
            rowsChanged();
        }

        private void updateFollowNewest(int first, int visible, int count) {
            View last = list.getChildAt(visible - 1);
            if (last == null) return;
            followNewest = !scrolling && first + visible >= count
                && last.getBottom() <= list.getHeight() - list.getPaddingBottom() + dp(2);
            jump.setVisibility(!followNewest && count > 1 ? View.VISIBLE : View.GONE);
        }

        private List<ProgressEntry> displayed() {
            return history.entries.isEmpty() ? fallback : history.entries;
        }

        void setCapturing(boolean value) {
            if (capturing == value) return;
            capturing = value;
            title.setTextSize(capturing ? 16 : 14);
            rowsChanged();
        }

        private void rowsChanged() {
            View first = list.getChildAt(0);
            Long anchor = first == null ? null : (Long) first.getTag();
            int offset = first == null ? 0 : first.getTop() - list.getPaddingTop();
            boolean follow = followNewest;
            rows.notifyDataSetChanged();
            if (rows.getCount() == 0) return;
            if (follow || anchor == null) {
                list.setSelection(rows.getCount() - 1);
            } else {
                int index = anchor > 0 ? history.indexOf(anchor) : list.getFirstVisiblePosition();
                if (index >= 0 && index < rows.getCount() && index != list.getFirstVisiblePosition()) {
                    list.setSelectionFromTop(index, offset);
                }
            }
        }

        void refresh() {
            String configuredAddress = settings.getString("endpoint", "").replaceFirst("/$", "");
            String configuredSecret = settings.getString("key", "");
            if (!configuredAddress.equals(address) || !configuredSecret.equals(secret)) {
                connection++;
                if (address != null && !configuredAddress.equals(address)) {
                    fallback.clear();
                    emptyNotice = "";
                }
                address = configuredAddress;
                secret = configuredSecret;
                loading = false;
                refreshPending = false;
                retryAt = 0;
                clearedThrough = configuredAddress.equals(settings.getString("cleared_progress_endpoint", ""))
                    ? settings.getLong("cleared_progress_through", 0) : 0;
                history = new ProgressHistory();
                followNewest = true;
                rowsChanged();
            }
            if (!validEndpoint(address) || !secret.matches("[A-Za-z0-9_-]{24,120}")) return;
            if (loading) {
                refreshPending = true;
                return;
            }
            fetchPage(0);
        }

        private void fetchPage(long before) {
            loading = true;
            if (before == 0) refreshPending = false;
            int current = connection;
            String notebook = address, token = secret;
            progressRequests.execute(() -> {
                try {
                    JSONObject response = requestHistory(notebook, token, before);
                    JSONArray entries = response.getJSONArray("entries");
                    List<ProgressEntry> page = new ArrayList<>();
                    long last = 0;
                    for (int i = 0; i < entries.length(); i++) {
                        JSONObject item = entries.getJSONObject(i);
                        long id = item.getLong("id");
                        if (id <= last || (before > 0 && id >= before)) {
                            throw new java.io.IOException("Invalid progress entry ID");
                        }
                        page.add(new ProgressEntry(id, item.getString("text")));
                        last = id;
                    }
                    boolean more = response.getBoolean("more");
                    ui.post(() -> {
                        if (current != connection || isDestroyed()) return;
                        boolean hidden = page.removeIf(entry -> entry.id <= clearedThrough);
                        if (history.merge(page, before, more && !hidden)) updateDisplay();
                        finishFetch(true);
                    });
                } catch (Exception error) {
                    ui.post(() -> {
                        if (current == connection && !isDestroyed()) finishFetch(false);
                    });
                }
            });
        }

        private void finishFetch(boolean succeeded) {
            loading = false;
            retryAt = succeeded ? 0 : SystemClock.elapsedRealtime() + 5000;
            if (refreshPending && foreground) {
                refreshPending = false;
                fetchPage(0);
            }
        }

        void acceptLive(JSONObject result) {
            JSONArray events = result.optJSONArray("events"), ids = result.optJSONArray("event_ids");
            if (events == null || events.length() == 0) return;
            boolean withIds = ids != null && ids.length() == events.length();
            List<ProgressEntry> latest = new ArrayList<>();
            long previous = 0;
            for (int i = 0; i < events.length(); i++) {
                long id = withIds ? ids.optLong(i, 0) : -2 - i;
                if (withIds && id <= previous) return;
                if (!withIds || id > clearedThrough) latest.add(new ProgressEntry(id, events.optString(i)));
                previous = id;
            }
            if (withIds) {
                if (history.merge(latest, 0, true)) updateDisplay();
            } else if (history.entries.isEmpty() && saveFallback(latest)) {
                updateDisplay();
            }
        }

        private boolean saveFallback(List<ProgressEntry> entries) {
            StringBuilder cached = new StringBuilder("진행 기록");
            List<ProgressEntry> recent = new ArrayList<>();
            for (int i = Math.max(0, entries.size() - 6); i < entries.size(); i++) {
                String line = entries.get(i).text;
                recent.add(new ProgressEntry(-3 - recent.size(), line));
                cached.append('\n').append(line);
            }
            String value = cached.toString();
            long lastId = entries.isEmpty() ? 0 : Math.max(0, entries.get(entries.size() - 1).id);
            if (value.equals(settings.getString("last_progress", "")) && lastId == settings.getLong("last_progress_id", 0)) return false;
            settings.edit().putString("last_progress", value).putLong("last_progress_id", lastId)
                .putString("last_progress_endpoint", address).apply();
            fallback = recent;
            return true;
        }

        private void updateDisplay() {
            if (!history.entries.isEmpty()) saveFallback(history.entries);
            rowsChanged();
        }

        private final class ProgressRows extends BaseAdapter {
            public int getCount() {
                int count = displayed().size();
                return Math.max(1, count);
            }
            public ProgressEntry getItem(int index) {
                List<ProgressEntry> entries = displayed();
                return entries.isEmpty()
                    ? new ProgressEntry(-1, !emptyNotice.isEmpty() ? emptyNotice
                        : capturing ? "첫 사진 수신 대기 중" : "촬영을 시작하면 여기에 기록이 쌓입니다")
                    : entries.get(index);
            }
            public long getItemId(int index) { return getItem(index).id; }
            @Override public boolean hasStableIds() { return true; }

            public View getView(int index, View recycled, ViewGroup parent) {
                TextView row = recycled instanceof TextView ? (TextView) recycled : label("", 14, INK, false);
                row.setTextSize(capturing ? 16 : 14);
                row.setPadding(dp(14), dp(3), dp(14), dp(3));
                row.setLineSpacing(dp(3), 1f);
                ProgressEntry entry = getItem(index);
                CharSequence line = entry.text;
                if (entry.text.length() > 10 && entry.text.charAt(2) == ':' && entry.text.charAt(5) == ':') {
                    SpannableString timeAndMessage = new SpannableString(entry.text);
                    timeAndMessage.setSpan(new ForegroundColorSpan(MUTED), 0, 8, 0);
                    line = timeAndMessage;
                }
                row.setText(line);
                row.setTag(entry.id);
                return row;
            }
        }
    }

    private JSONObject requestHistory(String address, String key, long before) throws Exception {
        String path = before > 0 ? "/logs?before=" + before : "/logs";
        return requestProgress(address, key, path, "GET");
    }

    private JSONObject requestProgress(String address, String key, String path, String method) throws Exception {
        HttpURLConnection connection = openRequest(address, key, path, method, 2500);
        try {
            if (connection.getResponseCode() != 200) throw new java.io.IOException("Notebook rejected log history");
            try (BufferedReader response = new BufferedReader(
                    new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                StringBuilder body = new StringBuilder();
                char[] buffer = new char[4096];
                int read;
                while ((read = response.read(buffer)) != -1) body.append(buffer, 0, read);
                return new JSONObject(body.toString());
            }
        } finally { connection.disconnect(); }
    }

    private JSONObject request(CaptureRun captureRun, String path, byte[] contents, String last, boolean done, boolean draining) throws Exception {
        HttpURLConnection connection = openRequest(captureRun.address, captureRun.secret, path, "POST", contents == null ? 2500 : 12000);
        try {
            String session = captureRun.id;
            connection.setRequestProperty("X-Study-Session", session);
            if ("/poll".equals(path)) {
                connection.setRequestProperty("X-Study-Notices", "1");
                long now = SystemClock.elapsedRealtime();
                if (batteryManager != null && (!session.equals(powerRun) || now - powerReportedAt >= 15000)) {
                    int level = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                    if (level >= 0 && level <= 100) {
                        connection.setRequestProperty("X-Study-Power", level + ","
                            + (batteryManager.isCharging() ? "1" : "0") + "," + thermalStatus());
                        powerRun = session;
                        powerReportedAt = now;
                    }
                }
                if (!captureRun.range.isEmpty()) connection.setRequestProperty("X-Study-Range", captureRun.range);
            }
            if (draining) connection.setRequestProperty("X-Study-Mode", "drain");
            if (last != null) {
                connection.setRequestProperty("X-Packet", last);
                connection.setRequestProperty("X-Result", done ? "done" : "cancel");
            }
            if (contents != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "image/jpeg");
                connection.setFixedLengthStreamingMode(contents.length);
                try (java.io.OutputStream out = connection.getOutputStream()) { out.write(contents); }
            }
            if (connection.getResponseCode() != 200) throw new java.io.IOException("Notebook rejected the request");
            try (InputStream in = connection.getInputStream()) {
                return new JSONObject(new String(in.readAllBytes(), StandardCharsets.UTF_8));
            }
        } finally { connection.disconnect(); }
    }
    private HttpURLConnection openRequest(String address, String secret, String path, String method, int timeout) throws java.io.IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(address + path).openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(3000);
        connection.setReadTimeout(timeout);
        connection.setRequestMethod(method);
        connection.setRequestProperty("Authorization", "Bearer " + secret);
        return connection;
    }
    private static long[] readWaveform(JSONArray values) {
        if (values == null || values.length() < 4 || values.length() > 46 || values.length() % 2 != 0) return null;
        long[] waveform = new long[values.length()];
        boolean hasPulse = false;
        for (int i = 0; i < waveform.length; i++) {
            waveform[i] = values.optLong(i, -1);
            if (waveform[i] < 0 || waveform[i] > 1500) return null;
            if (i % 2 == 1 && waveform[i] > 0) hasPulse = true;
        }
        return hasPulse ? waveform : null;
    }

    private static final class HapticTimeline {
        final long[] offsets;

        HapticTimeline(long[] waveform) {
            offsets = new long[waveform.length + 1];
            for (int i = 0; i < waveform.length; i++) offsets[i + 1] = offsets[i] + waveform[i];
        }

        long duration() { return offsets[offsets.length - 1]; }

        int pulseAt(long elapsed) {
            for (int i = 1; i < offsets.length - 1; i += 2) {
                if (elapsed < offsets[i + 1]) return elapsed >= offsets[i] ? i : -1;
            }
            return -1;
        }
    }

    private static final class HapticSegment {
        final String label, marks;
        final long from, to;

        HapticSegment(String label, String marks, long from, long to) {
            this.label = label;
            this.marks = marks;
            this.from = from;
            this.to = to;
        }

        String caption() {
            String title = "체크 확인".equals(label) ? "내 답 확인" : "시작".equals(label) ? "답 도착" : label;
            return marks.isEmpty() ? title : title + " " + marks;
        }
    }

    private static final class HapticPattern {
        final HapticTimeline timeline;
        private final long[] waveform;
        private final JSONArray metadata;
        private final List<HapticSegment> segments = new ArrayList<>();
        private final String kind;
        private final int question, answer;

        HapticPattern(long[] waveform, JSONArray metadata, String kind, int question, int answer) {
            this.waveform = waveform;
            this.metadata = metadata;
            this.kind = kind;
            this.question = question;
            this.answer = answer;
            timeline = new HapticTimeline(waveform);
            if (metadata == null || metadata.length() > 12) return;
            long previousEnd = 0;
            for (int i = 0; i < metadata.length(); i++) {
                JSONObject part = metadata.optJSONObject(i);
                if (part == null) continue;
                String label = part.optString("label"), marks = part.optString("marks");
                long from = part.optLong("from_ms", -1), to = part.optLong("to_ms", -1);
                if (label.isEmpty() || label.length() > 24 || !marks.matches("[●▬━ ]{0,24}")
                        || from < previousEnd || to <= from || to > timeline.duration()) continue;
                segments.add(new HapticSegment(label, marks, from, to));
                previousEnd = to;
            }
        }

        String caption(long elapsed) {
            for (HapticSegment segment : segments) {
                if (elapsed < segment.from) return "쉬는 중 / 다음 " + segment.caption();
                if (elapsed < segment.to) return "지금 " + segment.caption();
            }
            return "진동 신호";
        }

        String summary() {
            String title = "rescan".equals(kind) ? "다시 촬영" : "check".equals(kind) ? "체크 확인" : "일반 답";
            StringBuilder digits = new StringBuilder();
            String option = "";
            if (kind.isEmpty()) {
                for (HapticSegment segment : segments) {
                    if ("다시 촬영".equals(segment.label) || "체크 확인".equals(segment.label)) title = segment.label;
                    if (segment.label.matches("문항 [0-9]")) digits.append(segment.label.charAt(3));
                    if (segment.label.matches("보기 [①②③④⑤]")) option = segment.label.substring(3);
                }
            }
            if ("체크 확인".equals(title)) title = "내 답 확인";
            if ("일반 답".equals(title)) title = "답 도착";
            String number = question > 0 ? String.valueOf(question) : digits.toString();
            if (answer >= 1 && answer <= 5) option = String.valueOf("①②③④⑤".charAt(answer - 1));
            if (number.isEmpty() && "다시 촬영".equals(title)) return title + " / 진행 기록 확인";
            return title + (number.isEmpty() ? "" : " / " + number + "번")
                + (option.isEmpty() ? "" : " / 보기 " + option);
        }

        String parts() {
            StringBuilder parts = new StringBuilder();
            for (HapticSegment segment : segments) {
                if (parts.length() > 0) parts.append(" / ");
                parts.append(segment.caption());
            }
            return parts.toString();
        }

        String saved() {
            JSONArray values = new JSONArray();
            for (long value : waveform) values.put(value);
            return new JSONArray().put(values).put(metadata).put(kind).put(question).put(answer).toString();
        }
    }

    private final class HapticStrip extends LinearLayout {
        private final TextView caption = label("", 14, INK, true);
        private final TextView sequence = label("", 11, MUTED, false);
        private final TextView legend = label("● 짧게  ▬ 길게", 11, MUTED, false);
        private final PulseTrack track = new PulseTrack();
        private final Runnable tick = this::refresh;
        private HapticPattern active, last;
        private long requestedAt;

        HapticStrip() {
            super(StudyActivity.this);
            setOrientation(VERTICAL);
            setPadding(dp(14), dp(5), dp(8), dp(5));
            setBackground(background(SURFACE, PANEL_RADIUS, EDGE));
            LinearLayout labels = new LinearLayout(StudyActivity.this);
            labels.setGravity(Gravity.CENTER_VERTICAL);
            caption.setSingleLine(true);
            caption.setEllipsize(TextUtils.TruncateAt.END);
            labels.addView(caption, new LinearLayout.LayoutParams(0, -2, 1f));
            legend.setMaxLines(1);
            legend.setPadding(dp(10), 0, dp(10), 0);
            labels.addView(legend, new LinearLayout.LayoutParams(-2, -2));
            updateLegend();
            Button help = button("신호 안내", false);
            help.setOnClickListener(v -> showHapticHelp());
            labels.addView(help, new LinearLayout.LayoutParams(-2, dp(36)));
            addView(labels, new LinearLayout.LayoutParams(-1, -2));
            track.setContentDescription("진동 신호 파형");
            LinearLayout.LayoutParams trackSpace = new LinearLayout.LayoutParams(-1, dp(15));
            trackSpace.topMargin = dp(2);
            trackSpace.setMarginEnd(dp(6));
            addView(track, trackSpace);
            sequence.setMaxLines(2);
            sequence.setEllipsize(TextUtils.TruncateAt.END);
            LinearLayout.LayoutParams sequenceSpace = new LinearLayout.LayoutParams(-1, -2);
            sequenceSpace.setMarginEnd(dp(6));
            addView(sequence, sequenceSpace);
        }

        void updateLegend() {
            legend.setVisibility(landscape ? View.VISIBLE : View.GONE);
        }

        void restore(String saved) {
            if (!saved.isEmpty()) {
                try {
                    JSONArray state = new JSONArray(saved);
                    long[] waveform = readWaveform(state.optJSONArray(0));
                    if (waveform != null) last = new HapticPattern(waveform, state.optJSONArray(1),
                        state.optString(2, ""), state.optInt(3), state.optInt(4));
                } catch (org.json.JSONException ignored) { }
            }
            refresh();
        }

        void start(HapticPattern pattern, long start) {
            active = pattern;
            requestedAt = start;
            refresh();
        }

        String finish(boolean complete) {
            if (complete && active != null) last = active;
            active = null;
            refresh();
            return complete && last != null ? last.saved() : "";
        }

        void refresh() {
            ui.removeCallbacks(tick);
            if (blackScreen) return;
            HapticPattern shown = active != null ? active : last;
            if (shown == null) {
                caption.setText("진동 신호 대기");
                sequence.setText("●● 답 도착   ▬▬ 다시 촬영   ▬● 내 답 확인");
                return;
            }
            long duration = shown.timeline.duration();
            long elapsed = active != null ? Math.min(duration, SystemClock.elapsedRealtime() - requestedAt) : duration;
            String text = shown.summary();
            if (!text.contentEquals(caption.getText())) caption.setText(text);
            String details = active != null ? shown.caption(elapsed) : shown.parts();
            if (!details.contentEquals(sequence.getText())) sequence.setText(details);
            track.setContentDescription("진동 파형, " + text);
            track.timeline = shown.timeline;
            track.elapsed = elapsed;
            track.invalidate();
            if (active != null && elapsed < duration) ui.postDelayed(tick, 33);
        }
    }

    private void showHapticHelp() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.VERTICAL);
        cards.setPadding(dp(16), dp(12), dp(16), dp(6));
        scroll.addView(cards);
        addSignalHelp(cards, "답 도착", "● ●  짧게 두 번", "이어서 문항 번호와 정답 보기가 울려요.");
        addSignalHelp(cards, "다시 촬영", "▬ ▬  길게 두 번", "신호에 나온 문항을 다시 비추세요. 번호가 없으면 진행 기록을 보세요.");
        addSignalHelp(cards, "내 답 확인", "▬ ●  길게, 짧게", "표시한 답이 풀이와 달라요. 해당 문항을 확인하세요.");
        TextView example = new TextView(this);
        example.setText("17번의 답이 ③이라면\n●●  /  ●  /  ▬●●  //  ●●●\n시작  /  1  /  7  //  보기 ③");
        example.setTextSize(14);
        example.setTextColor(INK);
        example.setPadding(dp(8), dp(4), dp(8), dp(4));
        cards.addView(example);
        TextView digits = new TextView(this);
        digits.setText("짧게 0.14초, 길게 0.62초. 한 자리 안에서는 0.24초 쉬고, 다음 자리 전에는 0.8초 쉬어요. 보기 전에는 1.5초 쉰 뒤 짧은 횟수만 세세요.\n\n1~4는 짧게 그 횟수만큼, 5는 길게 한 번이에요. 6~9는 길게 한 번에 나머지 횟수를 더해요. 0은 길게 두 번이에요.");
        digits.setTextSize(13);
        digits.setTextColor(MUTED);
        digits.setPadding(dp(8), dp(6), dp(8), dp(4));
        cards.addView(digits);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("진동이 울리면")
            .setView(scroll).setPositiveButton("닫기", null).show();
        if (dialog.getWindow() != null) dialog.getWindow().setLayout(
            Math.min(dp(520), getResources().getDisplayMetrics().widthPixels - dp(28)), -2);
    }

    private void addSignalHelp(LinearLayout cards, String title, String pattern, String action) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(8), dp(7), dp(8), dp(7));
        LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(-1, -2);
        layout.bottomMargin = dp(7);
        cards.addView(card, layout);

        TextView heading = new TextView(this);
        heading.setText(title);
        heading.setTextColor(INK);
        heading.setTextSize(16);
        heading.setTypeface(null, android.graphics.Typeface.BOLD);
        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.addView(heading, new LinearLayout.LayoutParams(0, -2, 1f));
        TextView pulse = new TextView(this);
        pulse.setText(pattern);
        pulse.setTextColor(GREEN);
        pulse.setTextSize(13);
        top.addView(pulse, new LinearLayout.LayoutParams(-2, -2));
        card.addView(top);
        TextView instruction = new TextView(this);
        instruction.setText(action);
        instruction.setTextColor(MUTED);
        instruction.setTextSize(13);
        card.addView(instruction);
    }

    private final class PulseTrack extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private HapticTimeline timeline;
        private long elapsed;

        PulseTrack() { super(StudyActivity.this); }

        @Override protected void onDraw(Canvas canvas) {
            if (timeline == null || timeline.duration() == 0) return;
            float scale = getWidth() / (float) timeline.duration();
            float pulseY = dp(2), pulseHeight = dp(7);
            int activePulse = timeline.pulseAt(elapsed);
            for (int i = 1; i < timeline.offsets.length - 1; i += 2) {
                long from = timeline.offsets[i], to = timeline.offsets[i + 1];
                if (to == from) continue;
                float left = from * scale, right = to * scale;
                paint.setColor(i == activePulse ? INK : elapsed >= to ? GREEN : PULSE_IDLE);
                canvas.drawRoundRect(left, pulseY, right, pulseY + pulseHeight,
                    pulseHeight / 2, pulseHeight / 2, paint);
            }
            float progressY = getHeight() - dp(3);
            paint.setColor(PULSE_BASE);
            canvas.drawRect(0, progressY, getWidth(), progressY + dp(2), paint);
            paint.setColor(GREEN);
            canvas.drawRect(0, progressY, elapsed * scale, progressY + dp(2), paint);
        }
    }

    private void applyHaptic(JSONObject result) {
        long visit = result.optLong("visit");
        if (activePacket != null && (!result.optBoolean("valid") || visit != activeVisit)) finishHaptic(false);
        JSONObject packet = result.optJSONObject("packet");
        if (activePacket != null || ackPacket != null || !result.optBoolean("valid") || packet == null) return;
        long[] waveform = readWaveform(packet.optJSONArray("timings"));
        if (waveform == null) return;
        int question = packet.optInt("question"), choice = packet.optInt("answer");
        String kind = packet.optString("kind", "answer");
        HapticPattern pattern = new HapticPattern(waveform, packet.optJSONArray("segments"), kind, question, choice);
        long duration = pattern.timeline.duration();
        activePacket = packet.optString("id");
        activeVisit = visit;
        if ("rescan".equals(kind)) {
            activeAnswer = question > 0 ? question + "번 다시 촬영" : "다시 촬영할 장면이 있습니다";
        } else if (question > 0 && choice >= 1 && choice <= 5) {
            String options = "①②③④⑤";
            int marked = packet.optInt("marked");
            if ("check".equals(kind) && marked >= 1 && marked <= 5) {
                activeAnswer = question + "번 체크 확인 " + options.charAt(marked - 1) + " → " + options.charAt(choice - 1);
            } else {
                String subject = packet.optString("subject");
                activeAnswer = (subject.isEmpty() ? "" : subject + " ")
                    + question + "번 보기 " + options.charAt(choice - 1);
            }
            watchMarksUntil = SystemClock.elapsedRealtime() + 90000;
        } else activeAnswer = null;
        if (activeAnswer != null) {
            showLastAnswer(activeAnswer + (packet.optBoolean("repeat") ? " 다시 진동 요청" : " 진동 요청"));
        }
        int strength = vibrationStrength();
        long requestedAt = SystemClock.elapsedRealtime();
        if (!vibrate(waveform, strength)) {
            stop("휴대폰에 진동을 요청하지 못했습니다. 설정의 진동 시험을 확인하세요.");
            return;
        }
        hapticStrip.start(pattern, requestedAt);
        Log.i("StudyAssist", "Haptic started question=" + packet.optInt("question")
            + " duration=" + duration + " strength=" + strength + " kind=" + kind);
        hapticEnd = () -> finishHaptic(true);
        ui.postDelayed(hapticEnd, duration);
    }
    private int vibrationStrength() {
        int saved = settings.getInt("strength", 70);
        if (saved == 170 && !settings.getBoolean("strength_range_updated", false)) return MAX_STRENGTH;
        return Math.max(MIN_STRENGTH, Math.min(MAX_STRENGTH, saved));
    }
    private boolean vibrate(long[] duration, int strength) {
        if (vibration == null || !vibration.hasVibrator()) return false;
        int[] amplitude = new int[duration.length];
        for (int i = 1; i < amplitude.length; i += 2) amplitude[i] = strength;
        VibrationEffect effect = vibration.hasAmplitudeControl()
            ? VibrationEffect.createWaveform(duration, amplitude, -1)
            : VibrationEffect.createWaveform(duration, -1);
        try {
            vibration.vibrate(effect);
            return true;
        } catch (SecurityException | IllegalArgumentException error) {
            Log.w("StudyAssist", "진동 요청 실패", error);
            return false;
        }
    }
    private void finishHaptic(boolean complete) {
        if (activePacket == null) return;
        if (hapticEnd != null) ui.removeCallbacks(hapticEnd);
        if (!complete && vibration != null) vibration.cancel();
        String pattern = hapticStrip.finish(complete);
        if (complete && activeAnswer != null) {
            String last = "마지막 진동 요청 " + activeAnswer;
            showLastAnswer(last);
            settings.edit().putString("last_answer", last).putString("last_haptic_pattern", pattern).apply();
        } else if (!complete) {
            showLastAnswer(savedLastAnswer());
        }
        activeAnswer = null;
        ackPacket = activePacket;
        ackDone = complete;
        activePacket = null;
    }
}
