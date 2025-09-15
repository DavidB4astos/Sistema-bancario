-- Criação do banco e usuário (execute no MySQL como root)
CREATE DATABASE IF NOT EXISTS banco_simples CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'banco_user'@'localhost' IDENTIFIED BY 'sua_senha_forte_aqui';
GRANT ALL PRIVILEGES ON banco_simples.* TO 'banco_user'@'localhost';
FLUSH PRIVILEGES;

USE banco_simples;

CREATE TABLE IF NOT EXISTS operations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  type ENUM('DEPÓSITO','SAQUE') NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX IF NOT EXISTS idx_operations_type ON operations (type);
CREATE INDEX IF NOT EXISTS idx_operations_created_at ON operations (created_at);

