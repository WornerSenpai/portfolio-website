package com.dragxsy.cms.data.model

import com.google.gson.annotations.SerializedName

data class User(
    val id: String,
    val email: String,
    val name: String
)

data class AuthResponse(
    val success: Boolean,
    val token: String?,
    val user: User?,
    val error: String?
)

data class OverviewStats(
    val categories: Int,
    val projects: Int,
    val published: Int,
    val drafts: Int
)

data class ActivityLog(
    val id: String,
    val action: String,
    @SerializedName("item_name") val itemName: String,
    val details: String?,
    val timestamp: String
)

data class OverviewResponse(
    val userGreeting: String,
    val stats: OverviewStats,
    val recentActivity: List<ActivityLog>
)

data class Category(
    val id: String,
    val name: String,
    val slug: String,
    @SerializedName("cover_asset_url") val coverAssetUrl: String?,
    @SerializedName("projects_count") val projectsCount: Int = 0,
    @SerializedName("sort_order") val sortOrder: Int = 0
)

data class Asset(
    val id: String,
    @SerializedName("project_id") val projectId: String?,
    val filename: String,
    @SerializedName("mime_type") val mimeType: String,
    @SerializedName("original_url") val originalUrl: String,
    @SerializedName("optimized_url") val optimizedUrl: String,
    @SerializedName("card_url") val cardUrl: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String,
    val width: Int,
    val height: Int,
    @SerializedName("size_bytes") val sizeBytes: Long
)

data class Project(
    val id: String,
    @SerializedName("category_id") val categoryId: String,
    @SerializedName("category_name") val categoryName: String?,
    val title: String,
    val slug: String,
    val description: String?,
    val year: String = "2026",
    @SerializedName("cover_asset_url") val coverAssetUrl: String?,
    val status: String = "draft", // draft, published, unpublished
    val featured: Int = 0,
    @SerializedName("sort_order") val sortOrder: Int = 0,
    val tags: List<String> = emptyList(),
    val assets: List<Asset> = emptyList()
)

data class CreateProjectRequest(
    val title: String,
    val categoryId: String,
    val description: String?,
    val status: String = "draft",
    val featured: Boolean = false,
    val coverAssetUrl: String? = null,
    val assetIds: List<String> = emptyList()
)

data class ApiResponse(
    val success: Boolean,
    val message: String?,
    val error: String?,
    val id: String?
)

data class UploadResponse(
    val success: Boolean,
    val asset: Asset?,
    val error: String?
)
