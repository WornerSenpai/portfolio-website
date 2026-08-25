package com.dragxsy.cms.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.dragxsy.cms.data.api.ApiClient
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class UploadWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val filePath = inputData.getString("file_path") ?: return Result.failure()
        val file = File(filePath)

        if (!file.exists()) return Result.failure()

        return try {
            setProgress(workDataOf("progress" to 10))

            val mimeType = when (file.extension.lowercase()) {
                "png" -> "image/png"
                "webp" -> "image/webp"
                "mp4" -> "video/mp4"
                else -> "image/jpeg"
            }

            val requestFile = file.asRequestBody(mimeType.toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

            setProgress(workDataOf("progress" to 50))
            val response = ApiClient.getService().uploadFile(body)

            if (response.isSuccessful && response.body()?.success == true) {
                val assetId = response.body()?.asset?.id ?: ""
                setProgress(workDataOf("progress" to 100))
                Result.success(workDataOf("asset_id" to assetId))
            } else {
                Result.retry()
            }
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
