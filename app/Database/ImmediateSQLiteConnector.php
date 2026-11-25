<?php

namespace App\Database;

use Illuminate\Database\Connectors\SQLiteConnector;

/** Guna ImmediateSqlitePdo bila transaction_mode = IMMEDIATE dan PHP < 8.4 (8.4+ dikendalikan Laravel sendiri). */
class ImmediateSQLiteConnector extends SQLiteConnector
{
    private bool $immediate = false;

    public function connect(array $config)
    {
        $this->immediate = version_compare(PHP_VERSION, '8.4.0', '<')
            && strtoupper((string) ($config['transaction_mode'] ?? '')) === 'IMMEDIATE';

        return parent::connect($config);
    }

    protected function createPdoConnection($dsn, $username, #[\SensitiveParameter] $password, $options)
    {
        return $this->immediate
            ? new ImmediateSqlitePdo($dsn, $username, $password, $options)
            : parent::createPdoConnection($dsn, $username, $password, $options);
    }
}
