<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class AuthTest extends TestCase
{
    use RefreshDatabase;

    private function owner(): User
    {
        return User::create([
            'name' => 'Helmi',
            'email' => 'owner@example.test',
            'password' => Hash::make('rahsia-kuat-123'),
            'role' => 'owner',
        ]);
    }

    public function test_guest_is_redirected_to_login(): void
    {
        $this->get('/')->assertRedirect('/login');
        $this->get('/office/state')->assertRedirect('/login');
    }

    public function test_wrong_password_shows_error(): void
    {
        $this->owner();

        $this->post('/login', ['email' => 'owner@example.test', 'password' => 'salah'])
            ->assertSessionHasErrors('email');

        $this->assertGuest();
    }

    public function test_correct_login_reaches_office_state(): void
    {
        $this->owner();

        $this->post('/login', ['email' => 'owner@example.test', 'password' => 'rahsia-kuat-123'])
            ->assertRedirect('/');

        $this->getJson('/office/state')
            ->assertOk()
            ->assertJsonStructure(['agents', 'events', 'generated_at']);
    }

    public function test_login_is_rate_limited_after_five_attempts(): void
    {
        $this->owner();

        for ($i = 0; $i < 5; $i++) {
            $this->post('/login', ['email' => 'owner@example.test', 'password' => 'salah']);
        }

        $this->post('/login', ['email' => 'owner@example.test', 'password' => 'salah'])
            ->assertStatus(429);
    }

    public function test_office_user_command_creates_user_with_role(): void
    {
        $this->artisan('office:user', [
            'email' => 'viewer@example.test',
            '--role' => 'viewer',
            '--password' => 'rahsia-kuat-123',
        ])->assertSuccessful();

        $this->assertDatabaseHas('users', ['email' => 'viewer@example.test', 'role' => 'viewer']);
    }
}
