package com.dragxsy.cms.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.dragxsy.cms.ui.screens.*

sealed class Screen(val route: String) {
    object Login : Screen("login")
    object Home : Screen("home")
    object Portfolio : Screen("portfolio")
    object CreateProject : Screen("create_project")
    object UploadQueue : Screen("upload_queue")
    object Settings : Screen("settings")
}

@Composable
fun NavGraph(navController: NavHostController) {
    NavHost(
        navController = navController,
        startDestination = Screen.Login.route
    ) {
        composable(Screen.Login.route) {
            LoginScreen(navController = navController)
        }
        composable(Screen.Home.route) {
            HomeScreen(navController = navController)
        }
        composable(Screen.Portfolio.route) {
            PortfolioScreen(navController = navController)
        }
        composable(Screen.CreateProject.route) {
            CreateProjectScreen(navController = navController)
        }
        composable(Screen.UploadQueue.route) {
            UploadQueueScreen(navController = navController)
        }
        composable(Screen.Settings.route) {
            SettingsScreen(navController = navController)
        }
    }
}
