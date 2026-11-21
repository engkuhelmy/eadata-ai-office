<!doctype html>
<html lang="ms">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login · AI Office Hub</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #1d1a17; color: #f5efe6; margin: 0; display: grid; place-items: center; min-height: 100vh; }
        form { width: min(340px, 90vw); display: grid; gap: 12px; }
        input { padding: 10px; border-radius: 6px; border: 1px solid #4a4238; background: #2a2521; color: inherit; }
        button { padding: 10px; border: 0; border-radius: 6px; background: #d97757; color: #1d1a17; font-weight: 600; cursor: pointer; }
        .error { color: #ff8a80; font-size: 14px; }
        label { font-size: 14px; display: flex; gap: 6px; align-items: center; }
    </style>
</head>
<body>
    <form method="POST" action="{{ route('login') }}">
        @csrf
        <h1 style="margin:0;font-size:22px;">AI Office Hub</h1>
        @if ($errors->any())
            <div class="error">{{ $errors->first() }}</div>
        @endif
        <input type="email" name="email" value="{{ old('email') }}" placeholder="Email" required autofocus>
        <input type="password" name="password" placeholder="Password" required>
        <label><input type="checkbox" name="remember" value="1"> Ingat saya</label>
        <button type="submit">Log masuk</button>
    </form>
</body>
</html>
