<?php

namespace Tests\Feature;

use App\Database\ImmediateSqlitePdo;
use Illuminate\Support\Facades\DB;
use PDO;
use PDOException;
use Tests\TestCase;

class SqliteTransactionModeTest extends TestCase
{
    private ?string $file = null;

    protected function tearDown(): void
    {
        if ($this->file !== null) {
            foreach (glob($this->file.'*') ?: [] as $f) {
                @unlink($f);
            }
        }
        parent::tearDown();
    }

    private function tempDb(): string
    {
        $this->file = storage_path('framework/testing/tx-'.uniqid().'.sqlite');
        @mkdir(dirname($this->file), 0777, true);
        $pdo = new PDO('sqlite:'.$this->file);
        $pdo->exec('PRAGMA journal_mode=WAL');
        $pdo->exec('CREATE TABLE t (id INTEGER PRIMARY KEY, v INTEGER)');
        $pdo->exec('INSERT INTO t VALUES (1, 0)');

        return $this->file;
    }

    private function other(string $file): PDO
    {
        $pdo = new PDO('sqlite:'.$file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $pdo->exec('PRAGMA busy_timeout = 50');

        return $pdo;
    }

    public function test_config_defaults(): void
    {
        $this->assertSame('IMMEDIATE', config('database.connections.sqlite.transaction_mode'));
        $this->assertSame('file', config('cache.limiter')); // rate limiter tak tulis ke SQLite
    }

    /** Transaksi Laravel pegang kunci tulis sejak BEGIN, jadi penulis lain menunggu (busy_timeout), bukan gagal di tengah. */
    public function test_laravel_sqlite_connection_begins_immediate(): void
    {
        if (DB::connection()->getDriverName() !== 'sqlite') {
            $this->markTestSkipped('SQLite sahaja');
        }
        if (version_compare(PHP_VERSION, '8.4.0', '<')) {
            $this->assertInstanceOf(ImmediateSqlitePdo::class, DB::connection()->getPdo());
        }
        $this->assertSame(1, DB::transaction(fn () => 1));
        $this->assertFalse(DB::connection()->getPdo()->inTransaction());
    }

    public function test_immediate_pdo_takes_write_lock_at_begin(): void
    {
        $file = $this->tempDb();
        $a = new ImmediateSqlitePdo('sqlite:'.$file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

        $a->beginTransaction();
        $this->assertTrue($a->inTransaction());

        try {
            $this->other($file)->exec('BEGIN IMMEDIATE');
            $this->fail('Penulis lain sepatutnya tersekat sebab A dah pegang kunci tulis');
        } catch (PDOException $e) {
            $this->assertStringContainsString('locked', $e->getMessage());
        }

        $a->exec('UPDATE t SET v = 5');
        $a->commit();
        $this->assertFalse($a->inTransaction());
        $this->assertSame(5, (int) $this->other($file)->query('SELECT v FROM t')->fetchColumn());
    }

    public function test_deferred_pdo_does_not_lock_at_begin(): void
    {
        $file = $this->tempDb();
        $a = new PDO('sqlite:'.$file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $a->beginTransaction(); // DEFERRED (tingkah laku asal PHP 8.3)

        $b = $this->other($file);
        $b->exec('BEGIN IMMEDIATE'); // berjaya: A belum pegang kunci, inilah punca konflik di tengah transaksi
        $b->exec('ROLLBACK');
        $a->rollBack();
        $this->assertTrue(true);
    }

    public function test_rollback_resets_state(): void
    {
        $file = $this->tempDb();
        $a = new ImmediateSqlitePdo('sqlite:'.$file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $a->beginTransaction();
        $a->exec('UPDATE t SET v = 9');
        $a->rollBack();

        $this->assertFalse($a->inTransaction());
        $this->assertSame(0, (int) $a->query('SELECT v FROM t')->fetchColumn());
        $this->other($file)->exec('BEGIN IMMEDIATE'); // kunci dilepaskan
    }
}
