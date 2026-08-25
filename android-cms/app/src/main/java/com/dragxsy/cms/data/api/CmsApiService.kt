package com.dragxsy.cms.data.api

import com.dragxsy.cms.data.model.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

interface CmsApiService {

    @POST("api/cms/auth/login")
    suspend fun login(@Body credentials: Map<String, String>): Response<AuthResponse>

    @GET("api/cms/auth/me")
    suspend fun getMe(): Response<Map<String, User>>

    @GET("api/cms/overview")
    suspend fun getOverview(): Response<OverviewResponse>

    @GET("api/cms/categories")
    suspend fun getCategories(): Response<List<Category>>

    @POST("api/cms/categories")
    suspend fun createCategory(@Body data: Map<String, String>): Response<ApiResponse>

    @PUT("api/cms/categories/{id}")
    suspend fun updateCategory(@Path("id") id: String, @Body data: Map<String, String>): Response<ApiResponse>

    @DELETE("api/cms/categories/{id}")
    suspend fun deleteCategory(@Path("id") id: String): Response<ApiResponse>

    @GET("api/cms/projects")
    suspend fun getProjects(
        @Query("status") status: String? = null,
        @Query("categoryId") categoryId: String? = null
    ): Response<List<Project>>

    @GET("api/cms/projects/{id}")
    suspend fun getProjectDetail(@Path("id") id: String): Response<Project>

    @POST("api/cms/projects")
    suspend fun createProject(@Body request: CreateProjectRequest): Response<ApiResponse>

    @PUT("api/cms/projects/{id}")
    suspend fun updateProject(@Path("id") id: String, @Body request: Map<String, Any>): Response<ApiResponse>

    @PUT("api/cms/projects/{id}/publish")
    suspend fun publishProject(@Path("id") id: String): Response<ApiResponse>

    @PUT("api/cms/projects/{id}/unpublish")
    suspend fun unpublishProject(@Path("id") id: String): Response<ApiResponse>

    @DELETE("api/cms/projects/{id}")
    suspend fun deleteProject(@Path("id") id: String): Response<ApiResponse>

    @Multipart
    @POST("api/cms/upload")
    suspend fun uploadFile(@Part file: MultipartBody.Part): Response<UploadResponse>

    @POST("api/cms/import-drive")
    suspend fun importDrive(): Response<ApiResponse>

    @GET("api/cms/activity")
    suspend fun getActivity(): Response<List<ActivityLog>>
}
