pluginManagement {
    repositories {
        google()            // ← 必须有！！！
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()            // ← 必须有！！！
        mavenCentral()
    }
}

rootProject.name = "HolidayCountdown"
include(":app")
