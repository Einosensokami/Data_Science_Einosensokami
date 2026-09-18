# 資料科學期中報告：第 1～6、8、9、17 題

各題各自放在一個資料夾，程式都從網站抓取資料。執行完成後，CSV 會產生在對應題目的資料夾內。

## 安裝套件

在專案根目錄執行：

```bash
python -m pip install -r requirements.txt
```

## 題目與輸出

1. `第1題_本週新片`：開眼電影網本週新片，輸出 `movies.csv`
2. `第2題_台銀牌價`：臺灣銀行最新牌告匯率，輸出 `bank.csv`
3. `第3題_腸病毒資料`：政府資料開放平臺腸病毒資料，輸出 `NHI_EnteroviralInfection.csv`
4. `第4題_博客來書籍`：博客來「演算法」書籍資料，輸出 `booklist.csv`
5. `第5題_電影票房排行榜`：開眼電影網台北週末票房，輸出 `Taipei_movies.csv`
6. `第6題_NBA球隊運動員`：CLE、HOU、GSW 的 2023–24 球季球員資料，輸出 `players.csv`
7. `第8題_近期上映強片`：開眼電影網近期上映推薦，輸出 `movies.csv`
8. `第9題_Google新聞`：Selenium 抓取 Google 新聞首頁各分類標題，輸出 `google_news.csv` 與 `google_news.txt`
9. `第17題_GitHub網頁資料`：Selenium 自動登入 GitHub，擷取附圖兩個提示區塊，輸出 `github_windows.csv` 與 `github_dashboard.png`

第 1～3 題可在專案根目錄執行對應指令：

```powershell
python "第1題_本週新片/main.py"
python "第2題_台銀牌價/main.py"
python "第3題_腸病毒資料/main.py"
```

## 第 4 題：博客來書籍資料

第 4 題搜尋博客來關鍵字「演算法」。每抓一頁就開啟一個新的可見 Chrome，載入包含該頁碼的搜尋結果網址；抓完後關閉瀏覽器，再以新的瀏覽器處理下一頁。

每頁會解析以下資料，跨頁去重後寫入 `第4題_博客來書籍/booklist.csv`：

- 書名
- 網址
- 作者
- 書價

在專案根目錄執行：

```powershell
python "第4題_博客來書籍/main.py"
```

執行時可看到每一頁各自開啟及關閉 Chrome。遇到下列情況時會停止：

- 頁面沒有商品
- 頁面內容全部重複
- 某頁筆數少於第一頁，代表已到最後一頁
- 博客來顯示「連線暫時異常」

若博客來顯示「連線暫時異常」，程式不會覆蓋既有的 CSV。請間隔一段時間後再執行，不要立即連續重試。

## 第 5 題：電影票房排行榜

第 5 題以 Selenium 開啟開眼電影網的「本週新片」頁，並模擬滑鼠操作：

1. 移入「電影」選單後，點選「票房排行榜」
2. 在台北週末票房排行榜點選 `more`
3. 將完整 20 筆排行輸出至 `第5題_電影票房排行榜/Taipei_movies.csv`

CSV 欄位為：排名、片名、本週票房、累計票房。

在專案根目錄執行：

```powershell
python "第5題_電影票房排行榜/main.py"
```

## 第 6 題：NBA 球隊運動員資料

使用 requests 抓取 Basketball Reference 三隊的 `2024.html`，再以 BeautifulSoup 解析「Roster and Stats」頁面的 Roster 球員名單。網址中的 2024 指 2023–24 球季。

在專案根目錄執行：

```powershell
python "第6題_NBA球隊運動員/main.py"
```

CSV 欄位為：球隊、背號、姓名、位置、體重、生日、經驗、大學。

- 球隊使用 `CLE`、`HOU`、`GSW` 代碼；體重保留網站的磅（lb）單位。
- 經驗為該球季開始前的 NBA/ABA 年資，`R` 表示新人；網站沒有大學資料時保留空白。
- 背號保留原文（例如 `00` 或同季多個背號）；若使用 Excel，請將背號欄以文字匯入以保留前導零。
- 輸出檔名為 `players.csv`，採 UTF-8 BOM 編碼。
- 三隊全部抓取成功後才輸出；連線失敗或找不到表格時停止，保留既有 CSV。

## 第 8 題：近期上映強片

使用 requests 與 BeautifulSoup，抓取開眼電影網[近期上映頁面](https://www.atmovies.com.tw/movie/next/)中「近期上映推薦」的全部電影。這是題目本週新片頁導覽列中的「近期上映」入口；依補充筆記，以目前的推薦區塊對應題目「近期上映強片」。範圍為推薦清單，不包含各週完整上映名單或側欄下拉選單。

在專案根目錄執行：

```powershell
python "第8題_近期上映強片/main.py"
```

程式逐筆列印名稱、上映時間及完整連結網址，並存至該題資料夾的 `movies.csv`。日期統一為 `YYYY/MM/DD`，CSV 使用 UTF-8 BOM，方便 Excel 顯示中文。上映日期依網站公告保留，不自行限制日期範圍；網站連線失敗、清單為空或必要欄位缺漏時，停止並保留既有 CSV。

## 第 9 題：Google 新聞

使用 Selenium 開啟 [Google 新聞臺灣繁體中文首頁](https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant)，列印網頁 title，並自動捲動至頁面高度與新聞連結數穩定後，輸出以下區塊內的全部新聞標題：

- 焦點提要下的「焦點新聞」與「地方新聞」
- 您的主題（包含各子主題的新聞）
- 更多新聞

```powershell
python "第9題_Google新聞/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器，加入 `--headless` 可在背景執行。程式依區塊標題定位，不依賴新聞的固定筆數；每個分類內依網址去重，同一則新聞若屬於不同分類會分別保留。

輸出至該題資料夾：`google_news.csv`（分類、標題、網址）與 `google_news.txt`（網頁標題及分類新聞清單），均採 UTF-8 BOM 編碼。抓取範圍是本次首頁載入的各區塊，不包含點入分類後的其他頁面或整個新聞資料庫。地方新聞依網站偵測地區而異，個人化及版面也可能影響內容；缺少分類時會明確提示「部分完成」，不將其他分類的新聞冒充缺少的內容。連線失敗或完全無法解析時保留既有輸出。

## 第 17 題：GitHub 網頁資料

在專案根目錄執行：

```powershell
python "第17題_GitHub網頁資料/main.py"
```

依提示輸入 GitHub 帳號與密碼（密碼輸入時會顯示，方便核對）。也可事先設定 `GITHUB_USERNAME`、`GITHUB_PASSWORD` 環境變數。程式會開啟可見 Chrome，自動填入登入表單並按下 Sign in；表單中的隱藏 `authenticity_token` 由瀏覽器正常提交，無須自行取得或硬編碼。

若出現二階段驗證、裝置驗證或其他互動驗證，請在瀏覽器內完成，程式最多等待 5 分鐘。GitHub 的驗證流程見[官方說明](https://docs.github.com/en/authentication/securing-your-account-and-data-secure/verifying-new-devices-when-signing-in)。

原始 PDF 第 11 頁指定的兩個紅框為：

| 視窗 | 標題 | 擷取內容 |
| --- | --- | --- |
| 1 | Create your first project | 左側建立第一個專案的說明文字 |
| 2 | Updates to your homepage feed | 中央首頁動態更新公告的說明文字 |

登入後程式擷取這兩個區塊的標題與段落、列印結果，並在第 17 題資料夾產生：

- `github_windows.csv`：視窗、標題、內容、頁面網址、狀態，採 UTF-8 BOM 編碼供 Excel 開啟。
- `github_dashboard.png`：登入後目前畫面的截圖，供比對題目與報告使用。

題目截圖是舊版首頁；GitHub 已有[新版首頁配置](https://github.blog/changelog/2025-10-28-home-dashboard-update-in-public-preview/)，且既有專案的帳號不一定會看到第一個專案提示。程式找不到指定區塊時，會將 CSV 狀態標為「未顯示」、內容留空；只有找到標題時則標為「找到標題但無法解析內容」。這兩種狀態都不代表已完成該紅框擷取，需依截圖與老師確認是否接受目前頁面的替代區塊。

程式不儲存密碼、Cookie 或原始登入 HTML。CSV 與截圖可能含個人資料，已加入 `.gitignore`。執行需要已安裝 Chrome；Selenium 會管理對應的 WebDriver。
