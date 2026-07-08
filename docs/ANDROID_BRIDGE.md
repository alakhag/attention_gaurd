# Android Bridge

The included Android code is a bridge skeleton, not polished app-store code.

It contains:

```text
NotificationListenerService
BackendClient
MainActivity to open notification access settings
```

Needed before real phone testing:

```text
- open in Android Studio
- set BACKEND_URL in BackendClient.kt
- grant notification listener access
- run on Android phone
```

Then phone notifications will POST to:

```text
/backend-url/android/notifications
```
