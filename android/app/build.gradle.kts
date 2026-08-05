plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.lanfiletransfer.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.lanfiletransfer.android"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")

    // Added for QR pairing: Google Play Services' built-in scanning UI.
    // No camera permission needs to be declared in the manifest and no
    // CameraX/preview code is needed -- Play Services provides its own
    // full-screen scanner activity and just hands back the decoded text.
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
}
