package com.dragxsy.cms.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.dragxsy.cms.data.api.ApiClient
import com.dragxsy.cms.data.model.OverviewResponse
import com.dragxsy.cms.ui.navigation.Screen
import com.dragxsy.cms.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(navController: NavController) {
    val coroutineScope = rememberCoroutineScope()
    var overview by remember { mutableStateOf<OverviewResponse?>(null) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        coroutineScope.launch {
            try {
                val resp = ApiClient.getService().getOverview()
                if (resp.isSuccessful) {
                    overview = resp.body()
                }
            } catch (e: Exception) {
                // handle error
            } finally {
                isLoading = false
            }
        }
    }

    Scaffold(
        bottomBar = { BottomNavBar(navController, "home") }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(DarkBg)
                .padding(padding)
                .padding(20.dp)
        ) {
            Text(
                text = overview?.userGreeting ?: "Good morning, Sakshi",
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                color = AccentCyan,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Portfolio Overview",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                modifier = Modifier.padding(top = 2.dp, bottom = 20.dp)
            )

            // 4 Stats Cards
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatBox(title = "CATEGORIES", value = "${overview?.stats?.categories ?: 0}", modifier = Modifier.weight(1f))
                StatBox(title = "PROJECTS", value = "${overview?.stats?.projects ?: 0}", modifier = Modifier.weight(1f))
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatBox(title = "PUBLISHED", value = "${overview?.stats?.published ?: 0}", color = StatusPublished, modifier = Modifier.weight(1f))
                StatBox(title = "DRAFTS", value = "${overview?.stats?.drafts ?: 0}", color = StatusDraft, modifier = Modifier.weight(1f))
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Quick Actions
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = { navController.navigate(Screen.CreateProject.route) },
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentCyan),
                    modifier = Modifier.weight(1f).height(48.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = DarkBg)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("New Project", color = DarkBg, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
                }

                OutlinedButton(
                    onClick = { navController.navigate(Screen.UploadQueue.route) },
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                    modifier = Modifier.weight(1f).height(48.dp)
                ) {
                    Icon(Icons.Default.CloudUpload, contentDescription = null, tint = AccentCyan)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Upload", color = TextPrimary, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "RECENT ACTIVITY",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                color = TextSecondary,
                modifier = Modifier.padding(bottom = 10.dp)
            )

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(overview?.recentActivity ?: emptyList()) { log ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(CardBg, RoundedCornerShape(12.dp))
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(text = log.action, fontSize = 10.sp, color = AccentCyan, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                            Text(text = log.itemName, fontSize = 12.sp, color = TextPrimary, fontWeight = FontWeight.Medium)
                        }
                        Text(text = log.timestamp.split(" ").getOrElse(1) { "" }, fontSize = 10.sp, color = TextSecondary, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        }
    }
}

@Composable
fun StatBox(title: String, value: String, color: Color = TextPrimary, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .background(CardBg, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Text(text = title, fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = TextSecondary)
        Text(text = value, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = color, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 4.dp))
    }
}

@Composable
fun BottomNavBar(navController: NavController, current: String) {
    NavigationBar(containerColor = Color(0xFF0C1017)) {
        NavigationBarItem(
            selected = current == "home",
            onClick = { navController.navigate(Screen.Home.route) },
            label = { Text("Home", fontSize = 10.sp) },
            icon = { Icon(Icons.Default.Add, contentDescription = null) }
        )
        NavigationBarItem(
            selected = current == "portfolio",
            onClick = { navController.navigate(Screen.Portfolio.route) },
            label = { Text("Work", fontSize = 10.sp) },
            icon = { Icon(Icons.Default.Add, contentDescription = null) }
        )
        NavigationBarItem(
            selected = current == "upload",
            onClick = { navController.navigate(Screen.UploadQueue.route) },
            label = { Text("Upload", fontSize = 10.sp) },
            icon = { Icon(Icons.Default.CloudUpload, contentDescription = null) }
        )
        NavigationBarItem(
            selected = current == "settings",
            onClick = { navController.navigate(Screen.Settings.route) },
            label = { Text("Settings", fontSize = 10.sp) },
            icon = { Icon(Icons.Default.Add, contentDescription = null) }
        )
    }
}
