CREATE DATABASE opendkim;

USE opendkim;

CREATE TABLE `dkim_keys`(
	`id` INT AUTO_INCREMENT PRIMARY KEY,
	`domain_id` INT,
    `key_name` VARCHAR(255) UNIQUE
);

CREATE TABLE `domains`(
	`domain_id` INT AUTO_INCREMENT PRIMARY KEY,
	`domain` VARCHAR(255) UNIQUE
);

CREATE TABLE `signing`(
	`domain_id` INT UNIQUE,
	`key_id` INT UNIQUE
);
