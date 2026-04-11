# Mobile App 架構參考

> PM 參考此文件，根據專案需求調整後放入 `{workDir}/.knowledge/`

---

## 架構模式

### React Native 推薦結構

```
src/
├── components/           # 共用元件
│   ├── common/           # 基礎元件
│   └── {domain}/         # 業務元件
├── screens/              # 畫面
├── navigation/           # 導航設定
├── stores/               # 狀態管理
├── services/             # API 呼叫
├── hooks/                # 自訂 Hooks
├── utils/                # 工具函數
├── types/                # 型別定義
└── assets/               # 圖片、字體
```

### Flutter 推薦結構

```
lib/
├── core/                 # 共用核心
│   ├── theme/            # 主題
│   ├── routes/           # 路由
│   └── utils/            # 工具
├── features/             # 功能模組
│   └── {feature}/
│       ├── data/         # 資料層（Repository, Model）
│       ├── domain/       # 領域層（Entity, UseCase）
│       └── presentation/ # 展示層（Screen, Widget, State）
└── shared/               # 共用元件
```

## 導航設計

- 主要導航: Tab Navigator（底部分頁）或 Drawer
- 畫面堆疊: Stack Navigator
- 深層連結: 支援 URL scheme

## 狀態管理原則

- 全域狀態: 使用者資訊、認證狀態、設定
- 功能狀態: 各功能模組自行管理
- UI 狀態: 留在元件本地

## API 層設計

- 統一的 API client（處理認證、錯誤、重試）
- Token 自動刷新（Access Token 過期時自動用 Refresh Token）
- 離線支援策略（cache-first / network-first）

## 效能考量

- 圖片: 懶載入、快取、適當壓縮
- 列表: 虛擬捲動（FlatList / ListView.builder）
- 動畫: 使用原生驅動（useNativeDriver / Rive）
- 啟動: 減少初始化邏輯，使用 Splash Screen

## 測試策略

| 層級 | 工具建議 | 覆蓋目標 |
|------|---------|---------|
| 單元測試 | Jest / Flutter Test | 核心邏輯 >= 80% |
| 元件測試 | React Native Testing Library / WidgetTester | 關鍵元件 |
| E2E 測試 | Detox / Integration Test | 核心用戶流程 |

## 發佈

- iOS: TestFlight（測試）→ App Store Connect（正式）
- Android: Internal Track（測試）→ Google Play Console（正式）
- 版本號: SemVer（Major.Minor.Patch）+ Build Number
