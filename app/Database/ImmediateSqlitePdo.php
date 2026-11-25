<?php

namespace App\Database;

use PDO;
use PDOException;

/**
 * PDO SQLite yang mula transaksi dengan BEGIN IMMEDIATE (PHP 8.3).
 *
 * Laravel hanya hormati 'transaction_mode' pada PHP 8.4+. Pada 8.3, beginTransaction() = BEGIN DEFERRED, jadi
 * transaksi baca-kemudian-tulis (queue pop, cache increment) gagal "database is locked" serta-merta tanpa
 * menunggu busy_timeout bila penulis lain masuk di tengah. IMMEDIATE ambil kunci tulis di awal, jadi busy_timeout terpakai.
 */
class ImmediateSqlitePdo extends PDO
{
    private bool $open = false;

    public function beginTransaction(): bool
    {
        if ($this->open) {
            throw new PDOException('There is already an active transaction');
        }

        $this->exec('BEGIN IMMEDIATE');
        $this->open = true;

        return true;
    }

    public function commit(): bool
    {
        if (! $this->open) {
            throw new PDOException('There is no active transaction');
        }

        // Kalau COMMIT gagal (busy), transaksi masih terbuka: biar Laravel rollback.
        $this->exec('COMMIT');
        $this->open = false;

        return true;
    }

    public function rollBack(): bool
    {
        if (! $this->open) {
            throw new PDOException('There is no active transaction');
        }

        try {
            $this->exec('ROLLBACK');
        } catch (PDOException $e) {
            // SQLite dah rollback sendiri (cth. selepas ralat tertentu): anggap selesai
            if (! str_contains($e->getMessage(), 'no transaction is active')) {
                throw $e;
            }
        } finally {
            $this->open = false;
        }

        return true;
    }

    public function inTransaction(): bool
    {
        return $this->open;
    }
}
