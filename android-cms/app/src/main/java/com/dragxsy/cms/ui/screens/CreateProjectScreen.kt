package com.dragxsy.cms.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.dragxsy.cms.data.api.ApiClient
import com.dragxsy.cms.data.model.Category
import com.dragxsy.cms.data.model.CreateProjectRequest
import com.dragxsy.cms.ui.navigation.Screen
import com.dragxsy.cms.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun CreateProjectScreen(navController: NavController) {
    val coroutineScope = rememberCoroutineScope()

    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var selectedCategoryId by remember { mutableStateOf("") }
    var categories by remember { mutableStateOf<List<Category>>(emptyList()) }
    var isFeatured by remember { mutableStateOf(false) }
    var isSubmitting by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            try {
                val resp = ApiClient.getService().getCategories()
                if (resp.isSuccessful) {
                    categories = resp.body() ?: emptyList()
                    if (categories.isNotEmpty()) {
                        selectedCategoryId = categories.first().id
                    }
                }
            } catch (e: Exception) { }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBg)
            .padding(20.dp)
    ) {
        Row(modifier = Modifier.fillMaxWidth()) {
            IconButton(onClick = { navController.popBackStack() }) {
                Icon(Icons.Default.ArrowBack, contentDescription = null, tint = TextPrimary)
            }
            Text(
                text = "New Artwork Project",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                modifier = Modifier.padding(top = 10.dp, start = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        OutlinedTextField(
            value = title,
            onValueChange = { title = it },
            label = { Text("Project Title") },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp)
        )

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Description (Optional)") },
            modifier = Modifier.fillMaxWidth().height(120.dp),
            shape = RoundedCornerShape(16.dp)
        )

        Spacer(modifier = Modifier.height(24.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Button(
                onClick = {
                    isSubmitting = true
                    coroutineScope.launch {
                        try {
                            val req = CreateProjectRequest(
                                title = title,
                                categoryId = selectedCategoryId,
                                description = description,
                                status = "draft",
                                featured = isFeatured
                            )
                            val resp = ApiClient.getService().createProject(req)
                            if (resp.isSuccessful) {
                                navController.navigate(Screen.Home.route)
                            }
                        } finally {
                            isSubmitting = false
                        }
                    }
                },
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = CardBg),
                modifier = Modifier.weight(1f).height(50.dp)
            ) {
                Text("Save Draft", color = TextPrimary, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
            }

            Button(
                onClick = {
                    isSubmitting = true
                    coroutineScope.launch {
                        try {
                            val req = CreateProjectRequest(
                                title = title,
                                categoryId = selectedCategoryId,
                                description = description,
                                status = "published",
                                featured = isFeatured
                            )
                            val resp = ApiClient.getService().createProject(req)
                            if (resp.isSuccessful) {
                                navController.navigate(Screen.Home.route)
                            }
                        } finally {
                            isSubmitting = false
                        }
                    }
                },
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AccentCyan),
                modifier = Modifier.weight(1f).height(50.dp)
            ) {
                Text("Publish", color = DarkBg, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
            }
        }
    }
}
