# CoolPet Mobile — React Native / Expo Scaffold

This folder contains **static scaffold files** for the CoolPet mobile companion app.
It cannot run inside this Kubernetes container (Expo needs its own build environment),
but the source is ready to `cd mobile-app && npx expo install && npx expo start` on
any workstation.

## Structure

```
mobile-app/
├── package.json
├── app.json
├── App.js                    # navigator + auth context
├── screens/
│   ├── LoginScreen.js        # branded auth flow (email + password)
│   ├── MapScreen.js          # react-native-maps, custom pet marker
│   ├── HealthBottomSheet.js  # BPM / battery / speed drawer
│   └── GeofenceScreen.js     # radius slider
└── theme.js                  # shared design tokens (dark + gold)
```

## Backend endpoint

Set `EXPO_PUBLIC_API_URL` in `.env`:
```
EXPO_PUBLIC_API_URL=https://your-coolpet-backend.example.com
```

The screens hit the same REST endpoints as the web dashboard
(`/api/auth/login`, `/api/pets`, `/api/pets/:id/geofence`) and subscribe to the
same WebSocket at `wss://.../api/ws/live` for real-time collar updates.
