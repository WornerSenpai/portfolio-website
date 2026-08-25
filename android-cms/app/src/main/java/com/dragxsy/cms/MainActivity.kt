package com.dragxsy.cms

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import com.dragxsy.cms.data.api.ApiClient
import com.dragxsy.cms.ui.navigation.NavGraph
import com.dragxsy.cms.ui.theme.DarkBg
import com.dragxsy.cms.ui.theme.DragxsyCMSTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.init(this)

        setContent {
            DragxsyCMSTheme {
                Surface(
                    modifier = Modifier.fillMaxSize().background(DarkBg),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    NavGraph(navController = navController)
                }
            }
        }
    }
}
