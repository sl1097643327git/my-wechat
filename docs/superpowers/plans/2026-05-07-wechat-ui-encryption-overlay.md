# WeChat UI Encryption Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop companion tool that encrypts outgoing WeChat messages with one global shared key and displays decrypted ciphertext locally through a non-invasive overlay.

**Architecture:** Use a .NET 8 WPF desktop app because the product is Windows-only and needs first-class access to WPF windows, Win32 handles, Windows UI Automation, DPAPI, global hotkeys, and click-through topmost overlays. Keep the core crypto, message parsing, UI-recognition abstractions, and overlay placement logic in small testable classes, with the WPF project only wiring UI and Windows APIs together.

**Tech Stack:** .NET 8, WPF, xUnit, `System.Security.Cryptography`, Windows DPAPI through `ProtectedData`, Windows UI Automation through `System.Windows.Automation`, optional OCR adapter interface with a fake implementation in MVP tests.

---

## File Structure

Create a new .NET solution in the repository root.

- `WechatOverlay.sln` — solution file containing app and tests.
- `src/WechatOverlay.App/WechatOverlay.App.csproj` — WPF desktop application project.
- `src/WechatOverlay.App/App.xaml` and `src/WechatOverlay.App/App.xaml.cs` — WPF application startup.
- `src/WechatOverlay.App/MainWindow.xaml` and `src/WechatOverlay.App/MainWindow.xaml.cs` — main companion window with key entry, plaintext input, send button, status text, and overlay toggle.
- `src/WechatOverlay.App/Crypto/CryptoEnvelope.cs` — immutable envelope model for `ENC[v1]:...` messages.
- `src/WechatOverlay.App/Crypto/GlobalKeyEncryptor.cs` — PBKDF2 + AES-256-GCM encryption/decryption.
- `src/WechatOverlay.App/Crypto/KeyStorage.cs` — DPAPI-based optional local passphrase storage.
- `src/WechatOverlay.App/Messages/EncryptedMessageDetector.cs` — visible text parser for encrypted message prefixes.
- `src/WechatOverlay.App/Wechat/IWechatWindowLocator.cs` — abstraction for finding the active WeChat window.
- `src/WechatOverlay.App/Wechat/WechatWindowLocator.cs` — UI Automation window locator for desktop WeChat.
- `src/WechatOverlay.App/Wechat/IWechatMessageReader.cs` — abstraction for reading visible messages.
- `src/WechatOverlay.App/Wechat/UiAutomationMessageReader.cs` — UI Automation reader that extracts visible text and bounding rectangles.
- `src/WechatOverlay.App/Wechat/IWechatSender.cs` — abstraction for inserting ciphertext into WeChat.
- `src/WechatOverlay.App/Wechat/UiAutomationWechatSender.cs` — UI Automation sender with clipboard fallback.
- `src/WechatOverlay.App/Overlay/OverlayMessage.cs` — decrypted overlay message model.
- `src/WechatOverlay.App/Overlay/OverlayWindow.xaml` and `src/WechatOverlay.App/Overlay/OverlayWindow.xaml.cs` — transparent click-through topmost overlay.
- `src/WechatOverlay.App/Overlay/OverlayCoordinator.cs` — aligns decrypted overlay messages with WeChat message rectangles.
- `src/WechatOverlay.App/Hotkeys/GlobalHotkey.cs` — Win32 global hotkey registration for hide/show overlay.
- `src/WechatOverlay.App/Runtime/OverlayRefreshService.cs` — polling coordinator that reads visible messages, decrypts them, and updates the overlay.
- `tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj` — xUnit test project.
- `tests/WechatOverlay.Tests/Crypto/GlobalKeyEncryptorTests.cs` — crypto behavior tests.
- `tests/WechatOverlay.Tests/Messages/EncryptedMessageDetectorTests.cs` — encrypted message parser tests.
- `tests/WechatOverlay.Tests/Overlay/OverlayCoordinatorTests.cs` — overlay placement/filtering tests.
- `tests/WechatOverlay.Tests/Wechat/FakeWechatMessageReader.cs` — deterministic fake reader for service tests.
- `tests/WechatOverlay.Tests/Runtime/OverlayRefreshServiceTests.cs` — end-to-end refresh loop tests using fakes.

## Task 1: Scaffold solution and test projects

**Files:**
- Create: `WechatOverlay.sln`
- Create: `src/WechatOverlay.App/WechatOverlay.App.csproj`
- Create: `src/WechatOverlay.App/App.xaml`
- Create: `src/WechatOverlay.App/App.xaml.cs`
- Create: `src/WechatOverlay.App/MainWindow.xaml`
- Create: `src/WechatOverlay.App/MainWindow.xaml.cs`
- Create: `tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj`

- [ ] **Step 1: Create the solution and projects**

Run from repository root:

```powershell
dotnet new sln -n WechatOverlay
dotnet new wpf -n WechatOverlay.App -o src/WechatOverlay.App --framework net8.0-windows
dotnet new xunit -n WechatOverlay.Tests -o tests/WechatOverlay.Tests --framework net8.0-windows
dotnet sln WechatOverlay.sln add src/WechatOverlay.App/WechatOverlay.App.csproj
dotnet sln WechatOverlay.sln add tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj
dotnet add tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj reference src/WechatOverlay.App/WechatOverlay.App.csproj
```

Expected: both projects are added to `WechatOverlay.sln`, and the test project references the app project.

- [ ] **Step 2: Configure the app project for WPF and Windows APIs**

Replace `src/WechatOverlay.App/WechatOverlay.App.csproj` with:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <UseWPF>true</UseWPF>
    <SupportedOSPlatformVersion>10.0.17763.0</SupportedOSPlatformVersion>
  </PropertyGroup>
</Project>
```

- [ ] **Step 3: Configure the test project**

Replace `tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj` with:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0-windows</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="coverlet.collector" Version="6.0.2" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.10.0" />
    <PackageReference Include="xunit" Version="2.8.1" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.1" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\WechatOverlay.App\WechatOverlay.App.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 4: Run the baseline build and tests**

Run:

```powershell
dotnet build WechatOverlay.sln
dotnet test WechatOverlay.sln
```

Expected: build succeeds and the default xUnit test passes.

- [ ] **Step 5: Commit**

```powershell
git add WechatOverlay.sln src/WechatOverlay.App tests/WechatOverlay.Tests
git commit -m "chore: scaffold WeChat overlay app"
```

## Task 2: Add encrypted message envelope parsing

**Files:**
- Create: `src/WechatOverlay.App/Crypto/CryptoEnvelope.cs`
- Create: `tests/WechatOverlay.Tests/Crypto/CryptoEnvelopeTests.cs`

- [ ] **Step 1: Write failing envelope tests**

Create `tests/WechatOverlay.Tests/Crypto/CryptoEnvelopeTests.cs`:

```csharp
using WechatOverlay.App.Crypto;

namespace WechatOverlay.Tests.Crypto;

public sealed class CryptoEnvelopeTests
{
    [Fact]
    public void TryParseRejectsPlainText()
    {
        var parsed = CryptoEnvelope.TryParse("hello", out var envelope);

        Assert.False(parsed);
        Assert.Null(envelope);
    }

    [Fact]
    public void TryParseAcceptsVersionOnePrefix()
    {
        var parsed = CryptoEnvelope.TryParse("ENC[v1]:YWJj", out var envelope);

        Assert.True(parsed);
        Assert.NotNull(envelope);
        Assert.Equal(1, envelope.Version);
        Assert.Equal("YWJj", envelope.PayloadBase64Url);
    }

    [Fact]
    public void FormatCreatesVersionedMessage()
    {
        var text = CryptoEnvelope.FormatVersionOne("YWJj");

        Assert.Equal("ENC[v1]:YWJj", text);
    }
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter CryptoEnvelopeTests
```

Expected: fails because `CryptoEnvelope` does not exist.

- [ ] **Step 3: Implement the envelope model**

Create `src/WechatOverlay.App/Crypto/CryptoEnvelope.cs`:

```csharp
namespace WechatOverlay.App.Crypto;

public sealed record CryptoEnvelope(int Version, string PayloadBase64Url)
{
    public const string VersionOnePrefix = "ENC[v1]:";

    public static bool TryParse(string text, out CryptoEnvelope? envelope)
    {
        envelope = null;

        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        if (!text.StartsWith(VersionOnePrefix, StringComparison.Ordinal))
        {
            return false;
        }

        var payload = text[VersionOnePrefix.Length..].Trim();
        if (payload.Length == 0)
        {
            return false;
        }

        envelope = new CryptoEnvelope(1, payload);
        return true;
    }

    public static string FormatVersionOne(string payloadBase64Url)
    {
        if (string.IsNullOrWhiteSpace(payloadBase64Url))
        {
            throw new ArgumentException("Payload is required.", nameof(payloadBase64Url));
        }

        return VersionOnePrefix + payloadBase64Url;
    }
}
```

- [ ] **Step 4: Run envelope tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter CryptoEnvelopeTests
```

Expected: all `CryptoEnvelopeTests` pass.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Crypto/CryptoEnvelope.cs tests/WechatOverlay.Tests/Crypto/CryptoEnvelopeTests.cs
git commit -m "feat: add encrypted message envelope"
```

## Task 3: Add authenticated encryption with a global key

**Files:**
- Create: `src/WechatOverlay.App/Crypto/GlobalKeyEncryptor.cs`
- Create: `tests/WechatOverlay.Tests/Crypto/GlobalKeyEncryptorTests.cs`

- [ ] **Step 1: Write failing crypto tests**

Create `tests/WechatOverlay.Tests/Crypto/GlobalKeyEncryptorTests.cs`:

```csharp
using WechatOverlay.App.Crypto;

namespace WechatOverlay.Tests.Crypto;

public sealed class GlobalKeyEncryptorTests
{
    [Fact]
    public void EncryptThenDecryptReturnsPlaintext()
    {
        var encryptor = new GlobalKeyEncryptor();
        var cipherText = encryptor.Encrypt("shared secret", "你好，微信");

        var plainText = encryptor.Decrypt("shared secret", cipherText);

        Assert.Equal("你好，微信", plainText);
        Assert.StartsWith(CryptoEnvelope.VersionOnePrefix, cipherText, StringComparison.Ordinal);
    }

    [Fact]
    public void DecryptWithWrongKeyReturnsNull()
    {
        var encryptor = new GlobalKeyEncryptor();
        var cipherText = encryptor.Encrypt("shared secret", "hidden");

        var plainText = encryptor.Decrypt("wrong secret", cipherText);

        Assert.Null(plainText);
    }

    [Fact]
    public void DecryptMalformedMessageReturnsNull()
    {
        var encryptor = new GlobalKeyEncryptor();

        var plainText = encryptor.Decrypt("shared secret", "ENC[v1]:not-valid-base64");

        Assert.Null(plainText);
    }
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter GlobalKeyEncryptorTests
```

Expected: fails because `GlobalKeyEncryptor` does not exist.

- [ ] **Step 3: Implement `GlobalKeyEncryptor`**

Create `src/WechatOverlay.App/Crypto/GlobalKeyEncryptor.cs`:

```csharp
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace WechatOverlay.App.Crypto;

public sealed class GlobalKeyEncryptor
{
    private const int SaltSize = 16;
    private const int NonceSize = 12;
    private const int TagSize = 16;
    private const int KeySize = 32;
    private const int Pbkdf2Iterations = 210_000;

    public string Encrypt(string passphrase, string plaintext)
    {
        if (string.IsNullOrWhiteSpace(passphrase))
        {
            throw new ArgumentException("Passphrase is required.", nameof(passphrase));
        }

        var salt = RandomNumberGenerator.GetBytes(SaltSize);
        var nonce = RandomNumberGenerator.GetBytes(NonceSize);
        var key = DeriveKey(passphrase, salt);
        var plainBytes = Encoding.UTF8.GetBytes(plaintext);
        var cipherBytes = new byte[plainBytes.Length];
        var tag = new byte[TagSize];

        using var aes = new AesGcm(key, TagSize);
        aes.Encrypt(nonce, plainBytes, cipherBytes, tag);

        CryptographicOperations.ZeroMemory(key);

        var payload = new EncryptedPayload(
            Version: 1,
            Algorithm: "AES-256-GCM",
            Kdf: "PBKDF2-SHA256",
            Iterations: Pbkdf2Iterations,
            Salt: Convert.ToBase64String(salt),
            Nonce: Convert.ToBase64String(nonce),
            Ciphertext: Convert.ToBase64String(cipherBytes),
            Tag: Convert.ToBase64String(tag));

        var json = JsonSerializer.Serialize(payload);
        var base64Url = Base64UrlEncode(Encoding.UTF8.GetBytes(json));
        return CryptoEnvelope.FormatVersionOne(base64Url);
    }

    public string? Decrypt(string passphrase, string encryptedText)
    {
        if (!CryptoEnvelope.TryParse(encryptedText, out var envelope) || envelope is null)
        {
            return null;
        }

        try
        {
            var json = Encoding.UTF8.GetString(Base64UrlDecode(envelope.PayloadBase64Url));
            var payload = JsonSerializer.Deserialize<EncryptedPayload>(json);
            if (payload is null || payload.Version != 1 || payload.Algorithm != "AES-256-GCM")
            {
                return null;
            }

            var salt = Convert.FromBase64String(payload.Salt);
            var nonce = Convert.FromBase64String(payload.Nonce);
            var cipherBytes = Convert.FromBase64String(payload.Ciphertext);
            var tag = Convert.FromBase64String(payload.Tag);
            var key = DeriveKey(passphrase, salt, payload.Iterations);
            var plainBytes = new byte[cipherBytes.Length];

            using var aes = new AesGcm(key, TagSize);
            aes.Decrypt(nonce, cipherBytes, tag, plainBytes);
            CryptographicOperations.ZeroMemory(key);

            return Encoding.UTF8.GetString(plainBytes);
        }
        catch (ArgumentException)
        {
            return null;
        }
        catch (CryptographicException)
        {
            return null;
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static byte[] DeriveKey(string passphrase, byte[] salt, int iterations = Pbkdf2Iterations)
    {
        return Rfc2898DeriveBytes.Pbkdf2(
            Encoding.UTF8.GetBytes(passphrase),
            salt,
            iterations,
            HashAlgorithmName.SHA256,
            KeySize);
    }

    private static string Base64UrlEncode(byte[] bytes)
    {
        return Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    }

    private static byte[] Base64UrlDecode(string text)
    {
        var padded = text.Replace('-', '+').Replace('_', '/');
        padded += new string('=', (4 - padded.Length % 4) % 4);
        return Convert.FromBase64String(padded);
    }

    private sealed record EncryptedPayload(
        int Version,
        string Algorithm,
        string Kdf,
        int Iterations,
        string Salt,
        string Nonce,
        string Ciphertext,
        string Tag);
}
```

- [ ] **Step 4: Run crypto tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter GlobalKeyEncryptorTests
```

Expected: all `GlobalKeyEncryptorTests` pass.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Crypto/GlobalKeyEncryptor.cs tests/WechatOverlay.Tests/Crypto/GlobalKeyEncryptorTests.cs
git commit -m "feat: add global key encryption"
```

## Task 4: Detect encrypted visible messages

**Files:**
- Create: `src/WechatOverlay.App/Messages/EncryptedMessageDetector.cs`
- Create: `tests/WechatOverlay.Tests/Messages/EncryptedMessageDetectorTests.cs`

- [ ] **Step 1: Write failing detector tests**

Create `tests/WechatOverlay.Tests/Messages/EncryptedMessageDetectorTests.cs`:

```csharp
using WechatOverlay.App.Messages;

namespace WechatOverlay.Tests.Messages;

public sealed class EncryptedMessageDetectorTests
{
    [Fact]
    public void FindsEncryptedLinesOnly()
    {
        var detector = new EncryptedMessageDetector();
        var messages = detector.FindEncryptedMessages(new[]
        {
            "hello",
            "ENC[v1]:abc",
            " ENC[v1]:def "
        });

        Assert.Equal(new[] { "ENC[v1]:abc", "ENC[v1]:def" }, messages);
    }

    [Fact]
    public void IgnoresEmptyAndMalformedLines()
    {
        var detector = new EncryptedMessageDetector();
        var messages = detector.FindEncryptedMessages(new[]
        {
            "",
            "ENC[v2]:abc",
            "ENC[v1]:"
        });

        Assert.Empty(messages);
    }
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter EncryptedMessageDetectorTests
```

Expected: fails because `EncryptedMessageDetector` does not exist.

- [ ] **Step 3: Implement detector**

Create `src/WechatOverlay.App/Messages/EncryptedMessageDetector.cs`:

```csharp
using WechatOverlay.App.Crypto;

namespace WechatOverlay.App.Messages;

public sealed class EncryptedMessageDetector
{
    public IReadOnlyList<string> FindEncryptedMessages(IEnumerable<string> visibleTexts)
    {
        var results = new List<string>();

        foreach (var text in visibleTexts)
        {
            var trimmed = text.Trim();
            if (CryptoEnvelope.TryParse(trimmed, out _))
            {
                results.Add(trimmed);
            }
        }

        return results;
    }
}
```

- [ ] **Step 4: Run detector tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter EncryptedMessageDetectorTests
```

Expected: all `EncryptedMessageDetectorTests` pass.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Messages/EncryptedMessageDetector.cs tests/WechatOverlay.Tests/Messages/EncryptedMessageDetectorTests.cs
git commit -m "feat: detect encrypted messages"
```

## Task 5: Add WeChat UI Automation abstractions

**Files:**
- Create: `src/WechatOverlay.App/Wechat/WechatWindowInfo.cs`
- Create: `src/WechatOverlay.App/Wechat/VisibleWechatMessage.cs`
- Create: `src/WechatOverlay.App/Wechat/IWechatWindowLocator.cs`
- Create: `src/WechatOverlay.App/Wechat/WechatWindowLocator.cs`
- Create: `src/WechatOverlay.App/Wechat/IWechatMessageReader.cs`
- Create: `src/WechatOverlay.App/Wechat/UiAutomationMessageReader.cs`

- [ ] **Step 1: Add UI Automation package references if required by the SDK**

If `System.Windows.Automation` is unavailable during build, add this package:

```powershell
dotnet add src/WechatOverlay.App/WechatOverlay.App.csproj package UIAutomationClient --version 10.0.19041.0
```

Expected: the project can reference `System.Windows.Automation`.

- [ ] **Step 2: Create window and message models**

Create `src/WechatOverlay.App/Wechat/WechatWindowInfo.cs`:

```csharp
using System.Windows;

namespace WechatOverlay.App.Wechat;

public sealed record WechatWindowInfo(IntPtr Handle, Rect Bounds, string Title);
```

Create `src/WechatOverlay.App/Wechat/VisibleWechatMessage.cs`:

```csharp
using System.Windows;

namespace WechatOverlay.App.Wechat;

public sealed record VisibleWechatMessage(string Text, Rect Bounds);
```

- [ ] **Step 3: Create UI Automation interfaces**

Create `src/WechatOverlay.App/Wechat/IWechatWindowLocator.cs`:

```csharp
namespace WechatOverlay.App.Wechat;

public interface IWechatWindowLocator
{
    WechatWindowInfo? FindActiveWechatWindow();
}
```

Create `src/WechatOverlay.App/Wechat/IWechatMessageReader.cs`:

```csharp
namespace WechatOverlay.App.Wechat;

public interface IWechatMessageReader
{
    IReadOnlyList<VisibleWechatMessage> ReadVisibleMessages(WechatWindowInfo window);
}
```

- [ ] **Step 4: Implement WeChat window locator**

Create `src/WechatOverlay.App/Wechat/WechatWindowLocator.cs`:

```csharp
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;

namespace WechatOverlay.App.Wechat;

public sealed class WechatWindowLocator : IWechatWindowLocator
{
    public WechatWindowInfo? FindActiveWechatWindow()
    {
        var handle = GetForegroundWindow();
        if (handle == IntPtr.Zero)
        {
            return null;
        }

        var title = GetWindowTitle(handle);
        if (!title.Contains("微信", StringComparison.OrdinalIgnoreCase) &&
            !title.Contains("WeChat", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        if (!GetWindowRect(handle, out var rect))
        {
            return null;
        }

        return new WechatWindowInfo(
            handle,
            new Rect(rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top),
            title);
    }

    private static string GetWindowTitle(IntPtr handle)
    {
        var builder = new StringBuilder(256);
        _ = GetWindowText(handle, builder, builder.Capacity);
        return builder.ToString();
    }

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr hWnd, out NativeRect rect);

    private readonly struct NativeRect
    {
        public readonly int Left;
        public readonly int Top;
        public readonly int Right;
        public readonly int Bottom;
    }
}
```

- [ ] **Step 5: Implement visible message reader**

Create `src/WechatOverlay.App/Wechat/UiAutomationMessageReader.cs`:

```csharp
using System.Windows;
using System.Windows.Automation;

namespace WechatOverlay.App.Wechat;

public sealed class UiAutomationMessageReader : IWechatMessageReader
{
    public IReadOnlyList<VisibleWechatMessage> ReadVisibleMessages(WechatWindowInfo window)
    {
        var root = AutomationElement.FromHandle(window.Handle);
        if (root is null)
        {
            return Array.Empty<VisibleWechatMessage>();
        }

        var textCondition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Text);
        var elements = root.FindAll(TreeScope.Descendants, textCondition);
        var messages = new List<VisibleWechatMessage>();

        foreach (AutomationElement element in elements)
        {
            var text = element.Current.Name?.Trim();
            if (string.IsNullOrWhiteSpace(text))
            {
                continue;
            }

            var rect = element.Current.BoundingRectangle;
            if (rect.IsEmpty || rect.Width <= 0 || rect.Height <= 0)
            {
                continue;
            }

            messages.Add(new VisibleWechatMessage(text, new Rect(rect.X, rect.Y, rect.Width, rect.Height)));
        }

        return messages;
    }
}
```

- [ ] **Step 6: Build**

Run:

```powershell
dotnet build WechatOverlay.sln
```

Expected: build succeeds. If `System.Windows.Automation` resolution fails, complete Step 1 and rerun.

- [ ] **Step 7: Commit**

```powershell
git add src/WechatOverlay.App/Wechat src/WechatOverlay.App/WechatOverlay.App.csproj
git commit -m "feat: add WeChat UI automation readers"
```

## Task 6: Coordinate decryption results for overlay rendering

**Files:**
- Create: `src/WechatOverlay.App/Overlay/OverlayMessage.cs`
- Create: `src/WechatOverlay.App/Overlay/OverlayCoordinator.cs`
- Create: `tests/WechatOverlay.Tests/Overlay/OverlayCoordinatorTests.cs`

- [ ] **Step 1: Write failing coordinator tests**

Create `tests/WechatOverlay.Tests/Overlay/OverlayCoordinatorTests.cs`:

```csharp
using System.Windows;
using WechatOverlay.App.Crypto;
using WechatOverlay.App.Overlay;
using WechatOverlay.App.Wechat;

namespace WechatOverlay.Tests.Overlay;

public sealed class OverlayCoordinatorTests
{
    [Fact]
    public void CreatesOverlayMessageForDecryptableCiphertext()
    {
        var encryptor = new GlobalKeyEncryptor();
        var cipherText = encryptor.Encrypt("secret", "明文");
        var coordinator = new OverlayCoordinator(encryptor);

        var overlays = coordinator.BuildOverlayMessages("secret", new[]
        {
            new VisibleWechatMessage(cipherText, new Rect(10, 20, 200, 40)),
            new VisibleWechatMessage("normal", new Rect(10, 70, 200, 40))
        });

        var overlay = Assert.Single(overlays);
        Assert.Equal("明文", overlay.Plaintext);
        Assert.Equal(new Rect(10, 20, 200, 40), overlay.Bounds);
    }

    [Fact]
    public void SkipsWrongKeyCiphertext()
    {
        var encryptor = new GlobalKeyEncryptor();
        var cipherText = encryptor.Encrypt("secret", "明文");
        var coordinator = new OverlayCoordinator(encryptor);

        var overlays = coordinator.BuildOverlayMessages("wrong", new[]
        {
            new VisibleWechatMessage(cipherText, new Rect(10, 20, 200, 40))
        });

        Assert.Empty(overlays);
    }
}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter OverlayCoordinatorTests
```

Expected: fails because overlay classes do not exist.

- [ ] **Step 3: Implement overlay models and coordinator**

Create `src/WechatOverlay.App/Overlay/OverlayMessage.cs`:

```csharp
using System.Windows;

namespace WechatOverlay.App.Overlay;

public sealed record OverlayMessage(string Plaintext, Rect Bounds);
```

Create `src/WechatOverlay.App/Overlay/OverlayCoordinator.cs`:

```csharp
using WechatOverlay.App.Crypto;
using WechatOverlay.App.Wechat;

namespace WechatOverlay.App.Overlay;

public sealed class OverlayCoordinator(GlobalKeyEncryptor encryptor)
{
    public IReadOnlyList<OverlayMessage> BuildOverlayMessages(
        string passphrase,
        IEnumerable<VisibleWechatMessage> visibleMessages)
    {
        var overlays = new List<OverlayMessage>();

        foreach (var message in visibleMessages)
        {
            if (!CryptoEnvelope.TryParse(message.Text.Trim(), out _))
            {
                continue;
            }

            var plaintext = encryptor.Decrypt(passphrase, message.Text.Trim());
            if (!string.IsNullOrEmpty(plaintext))
            {
                overlays.Add(new OverlayMessage(plaintext, message.Bounds));
            }
        }

        return overlays;
    }
}
```

- [ ] **Step 4: Run coordinator tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter OverlayCoordinatorTests
```

Expected: all `OverlayCoordinatorTests` pass.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Overlay/OverlayMessage.cs src/WechatOverlay.App/Overlay/OverlayCoordinator.cs tests/WechatOverlay.Tests/Overlay/OverlayCoordinatorTests.cs
git commit -m "feat: build decrypted overlay messages"
```

## Task 7: Add transparent click-through overlay window

**Files:**
- Create: `src/WechatOverlay.App/Overlay/OverlayWindow.xaml`
- Create: `src/WechatOverlay.App/Overlay/OverlayWindow.xaml.cs`

- [ ] **Step 1: Create overlay XAML**

Create `src/WechatOverlay.App/Overlay/OverlayWindow.xaml`:

```xml
<Window x:Class="WechatOverlay.App.Overlay.OverlayWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        WindowStyle="None"
        AllowsTransparency="True"
        Background="Transparent"
        ShowInTaskbar="False"
        Topmost="True"
        ResizeMode="NoResize">
    <Canvas x:Name="MessageCanvas" IsHitTestVisible="False" />
</Window>
```

- [ ] **Step 2: Implement overlay rendering and click-through behavior**

Create `src/WechatOverlay.App/Overlay/OverlayWindow.xaml.cs`:

```csharp
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;

namespace WechatOverlay.App.Overlay;

public partial class OverlayWindow : Window
{
    private const int GwlExStyle = -20;
    private const int WsExTransparent = 0x00000020;
    private const int WsExLayered = 0x00080000;

    public OverlayWindow()
    {
        InitializeComponent();
        SourceInitialized += (_, _) => EnableClickThrough();
    }

    public void RenderMessages(IReadOnlyList<OverlayMessage> messages)
    {
        MessageCanvas.Children.Clear();

        foreach (var message in messages)
        {
            var border = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(230, 26, 115, 232)),
                CornerRadius = new CornerRadius(8),
                Padding = new Thickness(10, 6, 10, 6),
                Child = new TextBlock
                {
                    Text = message.Plaintext,
                    Foreground = Brushes.White,
                    FontSize = 14,
                    TextWrapping = TextWrapping.Wrap,
                    MaxWidth = Math.Max(120, message.Bounds.Width)
                }
            };

            Canvas.SetLeft(border, message.Bounds.X - Left);
            Canvas.SetTop(border, message.Bounds.Y - Top);
            MessageCanvas.Children.Add(border);
        }
    }

    public void Follow(Rect wechatBounds)
    {
        Left = wechatBounds.Left;
        Top = wechatBounds.Top;
        Width = wechatBounds.Width;
        Height = wechatBounds.Height;
    }

    private void EnableClickThrough()
    {
        var handle = new WindowInteropHelper(this).Handle;
        var style = GetWindowLong(handle, GwlExStyle);
        _ = SetWindowLong(handle, GwlExStyle, style | WsExTransparent | WsExLayered);
    }

    [DllImport("user32.dll")]
    private static extern int GetWindowLong(IntPtr hWnd, int index);

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hWnd, int index, int newStyle);
}
```

- [ ] **Step 3: Build**

Run:

```powershell
dotnet build WechatOverlay.sln
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```powershell
git add src/WechatOverlay.App/Overlay/OverlayWindow.xaml src/WechatOverlay.App/Overlay/OverlayWindow.xaml.cs
git commit -m "feat: add decrypted message overlay window"
```

## Task 8: Add WeChat sender with UI Automation and clipboard fallback

**Files:**
- Create: `src/WechatOverlay.App/Wechat/IWechatSender.cs`
- Create: `src/WechatOverlay.App/Wechat/UiAutomationWechatSender.cs`

- [ ] **Step 1: Create sender interface**

Create `src/WechatOverlay.App/Wechat/IWechatSender.cs`:

```csharp
namespace WechatOverlay.App.Wechat;

public interface IWechatSender
{
    bool SendText(WechatWindowInfo window, string text);
}
```

- [ ] **Step 2: Implement sender**

Create `src/WechatOverlay.App/Wechat/UiAutomationWechatSender.cs`:

```csharp
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Forms;

namespace WechatOverlay.App.Wechat;

public sealed class UiAutomationWechatSender : IWechatSender
{
    public bool SendText(WechatWindowInfo window, string text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return false;
        }

        SetForegroundWindow(window.Handle);

        var root = AutomationElement.FromHandle(window.Handle);
        if (root is null)
        {
            return false;
        }

        var editCondition = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit);
        var input = root.FindFirst(TreeScope.Descendants, editCondition);
        if (input is null)
        {
            return PasteAndSend(text);
        }

        if (input.TryGetCurrentPattern(ValuePattern.Pattern, out var pattern) && pattern is ValuePattern valuePattern)
        {
            valuePattern.SetValue(text);
            SendKeys.SendWait("{ENTER}");
            return true;
        }

        return PasteAndSend(text);
    }

    private static bool PasteAndSend(string text)
    {
        try
        {
            var previous = Clipboard.ContainsText() ? Clipboard.GetText() : null;
            Clipboard.SetText(text);
            SendKeys.SendWait("^v");
            SendKeys.SendWait("{ENTER}");

            if (previous is not null)
            {
                Clipboard.SetText(previous);
            }
            else
            {
                Clipboard.Clear();
            }

            return true;
        }
        catch (ExternalException)
        {
            return false;
        }
        catch (InvalidOperationException)
        {
            return false;
        }
    }

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);
}
```

- [ ] **Step 3: Add Windows Forms support for `SendKeys`**

Modify `src/WechatOverlay.App/WechatOverlay.App.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <UseWPF>true</UseWPF>
    <UseWindowsForms>true</UseWindowsForms>
    <SupportedOSPlatformVersion>10.0.17763.0</SupportedOSPlatformVersion>
  </PropertyGroup>
</Project>
```

- [ ] **Step 4: Build**

Run:

```powershell
dotnet build WechatOverlay.sln
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Wechat/IWechatSender.cs src/WechatOverlay.App/Wechat/UiAutomationWechatSender.cs src/WechatOverlay.App/WechatOverlay.App.csproj
git commit -m "feat: send encrypted text to WeChat"
```

## Task 9: Add refresh service and tests

**Files:**
- Create: `src/WechatOverlay.App/Runtime/OverlayRefreshService.cs`
- Create: `tests/WechatOverlay.Tests/Wechat/FakeWechatMessageReader.cs`
- Create: `tests/WechatOverlay.Tests/Runtime/OverlayRefreshServiceTests.cs`

- [ ] **Step 1: Write fake reader**

Create `tests/WechatOverlay.Tests/Wechat/FakeWechatMessageReader.cs`:

```csharp
using WechatOverlay.App.Wechat;

namespace WechatOverlay.Tests.Wechat;

public sealed class FakeWechatMessageReader(IReadOnlyList<VisibleWechatMessage> messages) : IWechatMessageReader
{
    public IReadOnlyList<VisibleWechatMessage> ReadVisibleMessages(WechatWindowInfo window) => messages;
}
```

- [ ] **Step 2: Write failing service test**

Create `tests/WechatOverlay.Tests/Runtime/OverlayRefreshServiceTests.cs`:

```csharp
using System.Windows;
using WechatOverlay.App.Crypto;
using WechatOverlay.App.Overlay;
using WechatOverlay.App.Runtime;
using WechatOverlay.App.Wechat;
using WechatOverlay.Tests.Wechat;

namespace WechatOverlay.Tests.Runtime;

public sealed class OverlayRefreshServiceTests
{
    [Fact]
    public void RefreshReturnsDecryptedOverlayMessages()
    {
        var encryptor = new GlobalKeyEncryptor();
        var cipher = encryptor.Encrypt("secret", "hello");
        var window = new WechatWindowInfo(new IntPtr(1), new Rect(0, 0, 800, 600), "微信");
        var reader = new FakeWechatMessageReader(new[]
        {
            new VisibleWechatMessage(cipher, new Rect(20, 30, 200, 40))
        });
        var service = new OverlayRefreshService(reader, new OverlayCoordinator(encryptor));

        var overlays = service.Refresh(window, "secret");

        var overlay = Assert.Single(overlays);
        Assert.Equal("hello", overlay.Plaintext);
    }
}
```

- [ ] **Step 3: Run test and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter OverlayRefreshServiceTests
```

Expected: fails because `OverlayRefreshService` does not exist.

- [ ] **Step 4: Implement refresh service**

Create `src/WechatOverlay.App/Runtime/OverlayRefreshService.cs`:

```csharp
using WechatOverlay.App.Overlay;
using WechatOverlay.App.Wechat;

namespace WechatOverlay.App.Runtime;

public sealed class OverlayRefreshService(
    IWechatMessageReader reader,
    OverlayCoordinator coordinator)
{
    public IReadOnlyList<OverlayMessage> Refresh(WechatWindowInfo window, string passphrase)
    {
        if (string.IsNullOrWhiteSpace(passphrase))
        {
            return Array.Empty<OverlayMessage>();
        }

        var visibleMessages = reader.ReadVisibleMessages(window);
        return coordinator.BuildOverlayMessages(passphrase, visibleMessages);
    }
}
```

- [ ] **Step 5: Run service tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter OverlayRefreshServiceTests
```

Expected: all `OverlayRefreshServiceTests` pass.


- [ ] **Step 6: Commit**

```powershell
git add src/WechatOverlay.App/Runtime tests/WechatOverlay.Tests/Wechat tests/WechatOverlay.Tests/Runtime
git commit -m "feat: refresh decrypted overlay messages"
```

## Task 10: Wire WPF main window to encryption, sending, and overlay refresh

**Files:**
- Modify: `src/WechatOverlay.App/MainWindow.xaml`
- Modify: `src/WechatOverlay.App/MainWindow.xaml.cs`
- Modify: `src/WechatOverlay.App/App.xaml`

- [ ] **Step 1: Replace main window XAML**

Replace `src/WechatOverlay.App/MainWindow.xaml` with:

```xml
<Window x:Class="WechatOverlay.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="WeChat Encryption Overlay"
        Width="520"
        Height="360"
        WindowStartupLocation="CenterScreen">
    <Grid Margin="16">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="*" />
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
        </Grid.RowDefinitions>

        <TextBlock Text="全局统一密钥" FontWeight="SemiBold" />
        <PasswordBox x:Name="PassphraseBox" Grid.Row="1" Margin="0,6,0,12" />

        <TextBox x:Name="PlaintextBox"
                 Grid.Row="2"
                 AcceptsReturn="True"
                 TextWrapping="Wrap"
                 VerticalScrollBarVisibility="Auto"
                 FontSize="14" />

        <StackPanel Grid.Row="3" Orientation="Horizontal" Margin="0,12,0,8">
            <Button x:Name="SendButton" Width="120" Height="32" Click="SendButton_Click">加密发送</Button>
            <Button x:Name="ToggleOverlayButton" Width="120" Height="32" Margin="8,0,0,0" Click="ToggleOverlayButton_Click">显示/隐藏蒙层</Button>
            <Button x:Name="RefreshButton" Width="120" Height="32" Margin="8,0,0,0" Click="RefreshButton_Click">刷新识别</Button>
        </StackPanel>

        <TextBlock x:Name="StatusText" Grid.Row="4" Text="等待检测微信窗口" Foreground="DimGray" />
    </Grid>
</Window>
```

- [ ] **Step 2: Replace main window code-behind**

Replace `src/WechatOverlay.App/MainWindow.xaml.cs` with:

```csharp
using System.Windows;
using WechatOverlay.App.Crypto;
using WechatOverlay.App.Overlay;
using WechatOverlay.App.Runtime;
using WechatOverlay.App.Wechat;

namespace WechatOverlay.App;

public partial class MainWindow : Window
{
    private readonly GlobalKeyEncryptor _encryptor = new();
    private readonly IWechatWindowLocator _windowLocator = new WechatWindowLocator();
    private readonly IWechatMessageReader _messageReader = new UiAutomationMessageReader();
    private readonly IWechatSender _sender = new UiAutomationWechatSender();
    private readonly OverlayWindow _overlayWindow = new();
    private readonly OverlayRefreshService _refreshService;
    private bool _overlayVisible = true;

    public MainWindow()
    {
        InitializeComponent();
        _refreshService = new OverlayRefreshService(_messageReader, new OverlayCoordinator(_encryptor));
        _overlayWindow.Show();
    }

    private void SendButton_Click(object sender, RoutedEventArgs e)
    {
        var passphrase = PassphraseBox.Password;
        var plaintext = PlaintextBox.Text;

        if (string.IsNullOrWhiteSpace(passphrase))
        {
            StatusText.Text = "请输入全局统一密钥";
            return;
        }

        if (string.IsNullOrWhiteSpace(plaintext))
        {
            StatusText.Text = "请输入要发送的明文";
            return;
        }

        var window = _windowLocator.FindActiveWechatWindow();
        if (window is null)
        {
            StatusText.Text = "未检测到微信窗口";
            return;
        }

        var encryptedText = _encryptor.Encrypt(passphrase, plaintext);
        if (_sender.SendText(window, encryptedText))
        {
            PlaintextBox.Clear();
            StatusText.Text = "已发送密文到微信";
            RefreshOverlay(window);
        }
        else
        {
            StatusText.Text = "发送失败：无法写入微信输入框";
        }
    }

    private void ToggleOverlayButton_Click(object sender, RoutedEventArgs e)
    {
        _overlayVisible = !_overlayVisible;
        _overlayWindow.Visibility = _overlayVisible ? Visibility.Visible : Visibility.Hidden;
        StatusText.Text = _overlayVisible ? "蒙层已显示" : "蒙层已隐藏";
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e)
    {
        var window = _windowLocator.FindActiveWechatWindow();
        if (window is null)
        {
            StatusText.Text = "未检测到微信窗口";
            return;
        }

        RefreshOverlay(window);
    }

    private void RefreshOverlay(WechatWindowInfo window)
    {
        _overlayWindow.Follow(window.Bounds);
        var overlays = _refreshService.Refresh(window, PassphraseBox.Password);
        _overlayWindow.RenderMessages(overlays);
        StatusText.Text = $"已识别 {overlays.Count} 条可解密消息";
    }
}
```

- [ ] **Step 3: Build**

Run:

```powershell
dotnet build WechatOverlay.sln
```

Expected: build succeeds.

- [ ] **Step 4: Manual smoke test**

Run:

```powershell
dotnet run --project src/WechatOverlay.App/WechatOverlay.App.csproj
```

Expected: the companion window opens, accepts a global key and plaintext, and shows clear status text when no WeChat window is focused.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/MainWindow.xaml src/WechatOverlay.App/MainWindow.xaml.cs src/WechatOverlay.App/App.xaml
git commit -m "feat: wire encryption overlay UI"
```

## Task 11: Add DPAPI key storage option

**Files:**
- Create: `src/WechatOverlay.App/Crypto/KeyStorage.cs`
- Create: `tests/WechatOverlay.Tests/Crypto/KeyStorageTests.cs`

- [ ] **Step 1: Write failing key storage test**

Create `tests/WechatOverlay.Tests/Crypto/KeyStorageTests.cs`:

```csharp
using WechatOverlay.App.Crypto;

namespace WechatOverlay.Tests.Crypto;

public sealed class KeyStorageTests
{
    [Fact]
    public void SaveLoadAndClearRoundTripsPassphrase()
    {
        var path = Path.Combine(Path.GetTempPath(), $"wechat-overlay-{Guid.NewGuid():N}.bin");
        var storage = new KeyStorage(path);

        storage.SavePassphrase("secret");
        var loaded = storage.LoadPassphrase();
        storage.Clear();

        Assert.Equal("secret", loaded);
        Assert.Null(storage.LoadPassphrase());
    }
}
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter KeyStorageTests
```

Expected: fails because `KeyStorage` does not exist.

- [ ] **Step 3: Implement key storage**

Create `src/WechatOverlay.App/Crypto/KeyStorage.cs`:

```csharp
using System.Security.Cryptography;
using System.Text;

namespace WechatOverlay.App.Crypto;

public sealed class KeyStorage
{
    private readonly string _path;

    public KeyStorage(string? path = null)
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        _path = path ?? Path.Combine(appData, "WechatOverlay", "global-key.bin");
    }

    public void SavePassphrase(string passphrase)
    {
        if (string.IsNullOrWhiteSpace(passphrase))
        {
            throw new ArgumentException("Passphrase is required.", nameof(passphrase));
        }

        var directory = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        var plainBytes = Encoding.UTF8.GetBytes(passphrase);
        var protectedBytes = ProtectedData.Protect(plainBytes, null, DataProtectionScope.CurrentUser);
        File.WriteAllBytes(_path, protectedBytes);
        CryptographicOperations.ZeroMemory(plainBytes);
    }

    public string? LoadPassphrase()
    {
        if (!File.Exists(_path))
        {
            return null;
        }

        try
        {
            var protectedBytes = File.ReadAllBytes(_path);
            var plainBytes = ProtectedData.Unprotect(protectedBytes, null, DataProtectionScope.CurrentUser);
            var passphrase = Encoding.UTF8.GetString(plainBytes);
            CryptographicOperations.ZeroMemory(plainBytes);
            return passphrase;
        }
        catch (CryptographicException)
        {
            return null;
        }
        catch (IOException)
        {
            return null;
        }
    }

    public void Clear()
    {
        if (File.Exists(_path))
        {
            File.Delete(_path);
        }
    }
}
```

- [ ] **Step 4: Run storage tests**

Run:

```powershell
dotnet test tests/WechatOverlay.Tests/WechatOverlay.Tests.csproj --filter KeyStorageTests
```

Expected: all `KeyStorageTests` pass.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Crypto/KeyStorage.cs tests/WechatOverlay.Tests/Crypto/KeyStorageTests.cs
git commit -m "feat: store global key with DPAPI"
```

## Task 12: Add global overlay toggle hotkey

**Files:**
- Create: `src/WechatOverlay.App/Hotkeys/GlobalHotkey.cs`
- Modify: `src/WechatOverlay.App/MainWindow.xaml.cs`

- [ ] **Step 1: Create global hotkey helper**

Create `src/WechatOverlay.App/Hotkeys/GlobalHotkey.cs`:

```csharp
using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace WechatOverlay.App.Hotkeys;

public sealed class GlobalHotkey : IDisposable
{
    private const int WmHotkey = 0x0312;
    private const uint ModControl = 0x0002;
    private const uint ModShift = 0x0004;
    private const uint VkD = 0x44;
    private readonly int _id;
    private readonly IntPtr _handle;
    private readonly HwndSource _source;
    private readonly Action _onPressed;

    public GlobalHotkey(IntPtr handle, int id, Action onPressed)
    {
        _handle = handle;
        _id = id;
        _onPressed = onPressed;
        _source = HwndSource.FromHwnd(handle);
        _source.AddHook(WndProc);
        _ = RegisterHotKey(_handle, _id, ModControl | ModShift, VkD);
    }

    public void Dispose()
    {
        _source.RemoveHook(WndProc);
        _ = UnregisterHotKey(_handle, _id);
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WmHotkey && wParam.ToInt32() == _id)
        {
            _onPressed();
            handled = true;
        }

        return IntPtr.Zero;
    }

    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
}
```

- [ ] **Step 2: Wire hotkey in main window**

Modify `src/WechatOverlay.App/MainWindow.xaml.cs` by adding these using statements:

```csharp
using System.Windows.Interop;
using WechatOverlay.App.Hotkeys;
```

Add this field to `MainWindow`:

```csharp
private GlobalHotkey? _toggleHotkey;
```

Add this override to `MainWindow`:

```csharp
protected override void OnSourceInitialized(EventArgs e)
{
    base.OnSourceInitialized(e);
    var handle = new WindowInteropHelper(this).Handle;
    _toggleHotkey = new GlobalHotkey(handle, 9001, ToggleOverlay);
}
```

Replace `ToggleOverlayButton_Click` with:

```csharp
private void ToggleOverlayButton_Click(object sender, RoutedEventArgs e)
{
    ToggleOverlay();
}
```

Add this method:

```csharp
private void ToggleOverlay()
{
    _overlayVisible = !_overlayVisible;
    _overlayWindow.Visibility = _overlayVisible ? Visibility.Visible : Visibility.Hidden;
    StatusText.Text = _overlayVisible ? "蒙层已显示" : "蒙层已隐藏";
}
```

Add this override:

```csharp
protected override void OnClosed(EventArgs e)
{
    _toggleHotkey?.Dispose();
    _overlayWindow.Close();
    base.OnClosed(e);
}
```

- [ ] **Step 3: Build**

Run:

```powershell
dotnet build WechatOverlay.sln
```

Expected: build succeeds.

- [ ] **Step 4: Manual hotkey test**

Run:

```powershell
dotnet run --project src/WechatOverlay.App/WechatOverlay.App.csproj
```

Expected: pressing `Ctrl+Shift+D` toggles the overlay visibility and updates status text.

- [ ] **Step 5: Commit**

```powershell
git add src/WechatOverlay.App/Hotkeys/GlobalHotkey.cs src/WechatOverlay.App/MainWindow.xaml.cs
git commit -m "feat: add overlay toggle hotkey"
```

## Task 13: Final verification and manual QA

**Files:**
- Modify files only if verification reveals issues caused by this implementation.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
dotnet test WechatOverlay.sln
```

Expected: all tests pass.

- [ ] **Step 2: Run full build**

Run:

```powershell
dotnet build WechatOverlay.sln -c Release
```

Expected: build succeeds with zero errors.

- [ ] **Step 3: Run manual no-WeChat QA**

Run:

```powershell
dotnet run --project src/WechatOverlay.App/WechatOverlay.App.csproj
```

Expected results:

- Empty key + send shows `请输入全局统一密钥`.
- Key + empty plaintext shows `请输入要发送的明文`.
- Key + plaintext with no active WeChat window shows `未检测到微信窗口`.
- Toggle button hides and shows overlay.
- `Ctrl+Shift+D` hides and shows overlay.

- [ ] **Step 4: Run manual WeChat QA**

Open Windows desktop WeChat and focus a chat. Run the app and verify:

- Key + plaintext sends a message beginning with `ENC[v1]:` to WeChat.
- The plaintext does not appear in the WeChat input box before encryption.
- Refresh recognizes visible `ENC[v1]:` messages when UI Automation exposes message text.
- Overlay follows WeChat when the WeChat window moves.
- Overlay hides immediately when toggled off.
- Wrong key does not show misleading plaintext.

- [ ] **Step 5: Document known limitations in README**

Create `README.md` if it does not exist, or add this section if it does:

```markdown
## WeChat Encryption Overlay

This Windows desktop companion app encrypts outgoing text with a shared global key and displays decrypted ciphertext locally through a transparent overlay. It does not hook, inject into, patch, reverse engineer, or read WeChat internals. It uses normal Windows UI mechanisms: UI Automation for window/message detection, clipboard or UI Automation for sending ciphertext, and a topmost WPF overlay for local plaintext display.

### Limitations

- Only visible messages can be decrypted in the overlay.
- UI Automation availability depends on the installed WeChat version.
- OCR fallback can be added behind `IWechatMessageReader` when UI Automation does not expose message text.
- A global key means all chats share one compromise domain.
- This does not protect against local malware, screenshots, screen recording, or endpoint compromise.
```

- [ ] **Step 6: Final commit**

```powershell
git add README.md
git commit -m "docs: describe WeChat overlay limitations"
```

## Self-Review Notes

- Spec coverage: The plan covers Windows desktop app, global shared key, no Hook/no injection boundary, tool-owned plaintext input, encrypt-to-WeChat sending, UI Automation recognition, overlay decryption display, DPAPI key storage, hotkey toggle, and manual QA.
- OCR fallback: The design requires OCR fallback, but this implementation plan intentionally isolates OCR behind `IWechatMessageReader` and ships UI Automation first. Add OCR as a follow-up task once UI Automation behavior is verified against the target WeChat version.
- Commit steps: Commit commands are included for workers following the plan. In this current session, do not run them unless the user explicitly requests commits.
