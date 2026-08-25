package com.dragxsy.cms.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.dragxsy.cms.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun PortfolioScreen(navController: NavController) {
    val coroutineScope = rememberCoroutineScope()
    var categories by remember { mutableStateOf<List<Category>>(emptyList()) }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            try {
                val resp = ApiClient.getService().getCategories()
                if (resp.isSuccessful) {
                    categories = resp.body() ?: emptyList()
                }
            } catch (e: Exception) { }
        }
    }

    Scaffold(bottomBar = { BottomNavBar(navController, "portfolio") }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().background(DarkBg).padding(padding).padding(20.dp)
        ) {
            Text("Portfolio", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
            Spacer(modifier = Modifier.height(16.dp))

            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(categories) { cat ->
                    Column(
                        modifier = Modifier.fillMaxWidth().background(CardBg, RoundedCornerShape(16.dp)).padding(16.dp)
                    ) {
                        Text(text = cat.name, fontWeight = FontWeight.Bold, fontSize = 16.sp, color = TextPrimary)
                        Text(text = "${cat.projectsCount} projects", fontSize = 11.sp, fontFamily = FontFamily.Monospace, color = TextSecondary)
                    }
                }
            }
        }
    }
}

@Composable
fun UploadQueueScreen(navController: NavController) {
    Scaffold(bottomBar = { BottomNavBar(navController, "upload") }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().background(DarkBg).padding(padding).padding(20.dp)
        ) {
            Text("Upload Queue", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Select files to upload in background via WorkManager", fontSize = 12.sp, color = TextSecondary)
        }
    }
}

@Composable
fun SettingsScreen(navController: NavController) {
    val coroutineScope = rememberCoroutineScope()
    var message by remember { mutableStateOf<String?>(null) }

    Scaffold(bottomBar = { BottomNavBar(navController, "settings") }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().background(DarkBg).padding(padding).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Settings", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)

            Button(
                onClick = {
                    coroutineScope.launch {
                        try {
                            val resp = ApiClient.getService().importDrive()
                            message = resp.body()?.message ?: "Drive imported"
                        } catch (e: Exception) {
                            message = "Error: ${e.localizedMessage}"
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = CardBg)
            ) {
                Text("Seed from Google Drive", color = AccentCyan, fontFamily = FontFamily.Monospace)
            }

            message?.let {
                Text(text = it, color = AccentCyan, fontSize = 12.sp)
            }
        }
    }
}
