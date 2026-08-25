package com.dragxsy.cms.data.api

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var baseUrl = "http://10.0.2.2:5000/" // Android Emulator default for localhost
    private var token: String? = null
    private var service: CmsApiService? = null

    fun init(context: Context, customUrl: String? = null) {
        if (!customUrl.isNullOrEmpty()) {
            baseUrl = if (customUrl.endsWith("/")) customUrl else "$customUrl/"
        }

        try {
            val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            val prefs: SharedPreferences = EncryptedSharedPreferences.create(
                "cms_secure_prefs",
                masterKeyAlias,
                context,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            token = prefs.getString("auth_token", null)
        } catch (e: Exception) {
            val prefs = context.getSharedPreferences("cms_prefs", Context.MODE_PRIVATE)
            token = prefs.getString("auth_token", null)
        }

        buildRetrofit()
    }

    fun setToken(context: Context, newToken: String?) {
        token = newToken
        try {
            val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            val prefs = EncryptedSharedPreferences.create(
                "cms_secure_prefs",
                masterKeyAlias,
                context,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            prefs.edit().putString("auth_token", newToken).apply()
        } catch (e: Exception) {
            val prefs = context.getSharedPreferences("cms_prefs", Context.MODE_PRIVATE)
            prefs.edit().putString("auth_token", newToken).apply()
        }
        buildRetrofit()
    }

    fun getToken(): String? = token

    private fun buildRetrofit() {
        val authInterceptor = Interceptor { chain ->
            val requestBuilder = chain.request().newBuilder()
            token?.let {
                requestBuilder.addHeader("Authorization", "Bearer $it")
            }
            chain.proceed(requestBuilder.build())
        }

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        service = retrofit.create(CmsApiService::class.java)
    }

    fun getService(): CmsApiService {
        if (service == null) {
            buildRetrofit()
        }
        return service!!
    }
}
