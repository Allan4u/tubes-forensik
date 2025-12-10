import android.Manifest;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import com.google.android.material.button.MaterialButton;
import com.google.gson.Gson;
import java.util.ArrayList;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;

public class MainActivity extends AppCompatActivity implements LocationListener {

    private static final String BRIDGE_TAG = "LOCSHIELD_BRIDGE";
    private static final Gson gson = new Gson();
    static class Payload { String event, source, msg; int risk; Payload(String e, String s, int r, String m){this.event=e;this.source=s;this.risk=r;this.msg=m;}}

    private TextView tvStatus, tvConsole;
    private MaterialButton btnAudit, btnAttack;
    private LocationManager locationManager;
    private boolean isAttacking = false;
    private Timer attackTimer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main); // Pastikan layout XML ada dan ID-nya benar

        tvStatus = findViewById(R.id.tvStatus); // ID di XML harus: tvStatus
        tvConsole = findViewById(R.id.tvConsole); // ID di XML harus: tvConsole
        btnAudit = findViewById(R.id.btnAudit); // ID di XML harus: btnAudit
        btnAttack = findViewById(R.id.btnAttack); // ID di XML harus: btnAttack

        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);

        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, 1);
        }

        btnAudit.setOnClickListener(v -> performAudit());
        btnAttack.setOnClickListener(v -> { if(!isAttacking) startAttack(); else stopAttack(); });
    }

    private void performAudit() {
        PackageManager pm = getPackageManager();
        List<PackageInfo> pkgs = pm.getInstalledPackages(PackageManager.GET_PERMISSIONS);
        List<String> risky = new ArrayList<>();
        for(PackageInfo p : pkgs) {
            if(p.requestedPermissions != null) {
                for(String perm : p.requestedPermissions) {
                    if(perm.equals(Manifest.permission.ACCESS_FINE_LOCATION) && (p.applicationInfo.flags & ApplicationInfo.FLAG_SYSTEM) == 0) {
                        risky.add(p.packageName);
                    }
                }
            }
        }
        sendToPython("AUDIT_RESULT", "Apps with GPS: " + risky.toString(), 5);
        tvConsole.setText("Audit Found: " + risky.size() + " apps");
    }

    private void startAttack() {
        isAttacking = true;
        btnAttack.setText("STOP ATTACK");
        btnAttack.setBackgroundColor(Color.RED);
        tvStatus.setText("SYSTEM UNDER ATTACK");
        tvStatus.setTextColor(Color.RED);

        attackTimer = new Timer();
        attackTimer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                new Handler(Looper.getMainLooper()).post(() -> {
                    try {
                        if (ActivityCompat.checkSelfPermission(MainActivity.this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                            locationManager.requestSingleUpdate(LocationManager.GPS_PROVIDER, MainActivity.this, null);
                        }
                    } catch (Exception e) {}
                });
                sendToPython("THREAT_EVENT", "HIGH_FREQ_ACCESS | DoS Attack Simulation", 10);
            }
        }, 0, 100);
    }

    private void stopAttack() {
        isAttacking = false;
        if(attackTimer != null) attackTimer.cancel();
        btnAttack.setText("SIMULATE ATTACK");
        btnAttack.setBackgroundColor(Color.parseColor("#EF4444"));
        tvStatus.setText("SYSTEM SECURE");
        tvStatus.setTextColor(Color.GREEN);
        sendToPython("INFO", "Attack Stopped", 0);
    }

    private void sendToPython(String event, String msg, int risk) {
        String json = gson.toJson(new Payload(event, getPackageName(), risk, msg));
        Log.e(BRIDGE_TAG, json);
    }

    @Override public void onLocationChanged(@NonNull Location location) {}
    @Override public void onStatusChanged(String provider, int status, Bundle extras) {}
    @Override public void onProviderEnabled(@NonNull String provider) {}
    @Override public void onProviderDisabled(@NonNull String provider) {}
}