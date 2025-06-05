-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jun 03, 2025 at 06:48 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `automated_shopping_cart`
--

-- --------------------------------------------------------

--
-- Table structure for table `analytics`
--

CREATE TABLE `analytics` (
  `id` int(11) NOT NULL,
  `event_type` varchar(50) DEFAULT NULL,
  `reference_id` int(11) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `timestamp` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `commands`
--

CREATE TABLE `commands` (
  `id` int(11) NOT NULL,
  `command_type` enum('open_lid','weigh_item','write_tag','reset_tag','BUZZER','LED','OPEN_LID','CLOSE_LID','_control_read_flag','read_tag','tare','READC') NOT NULL,
  `parameters` text DEFAULT NULL,
  `status` enum('pending','complete') DEFAULT 'pending',
  `timestamp` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `commands`
--

INSERT INTO `commands` (`id`, `command_type`, `parameters`, `status`, `timestamp`) VALUES
(272, 'BUZZER', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:19'),
(273, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:22'),
(274, 'CLOSE_LID', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:26'),
(275, 'open_lid', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:28'),
(276, 'CLOSE_LID', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:31'),
(277, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:53'),
(278, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 15:09:59'),
(279, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 15:10:00'),
(280, 'BUZZER', '{\"control_mode\": true}', 'complete', '2025-05-02 15:10:02'),
(281, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:08:40'),
(282, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:16:13'),
(283, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:16:33'),
(284, '_control_read_flag', '{\"purpose\": \"control_read_only\"}', 'complete', '2025-05-02 16:16:57'),
(285, 'read_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:16:57'),
(286, '_control_read_flag', '{}', 'complete', '2025-05-02 16:16:57'),
(287, '_control_read_flag', '{\"purpose\": \"control_read_only\"}', 'complete', '2025-05-02 16:17:59'),
(288, 'read_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:17:59'),
(289, '_control_read_flag', '{}', 'complete', '2025-05-02 16:17:59'),
(290, '_control_read_flag', '{\"purpose\": \"control_read_only\"}', 'complete', '2025-05-02 16:19:09'),
(291, 'read_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:19:09'),
(292, '_control_read_flag', '{}', 'complete', '2025-05-02 16:19:09'),
(293, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:20:25'),
(294, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:22:39'),
(295, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:23:05'),
(296, 'weigh_item', '{\"control_mode\": true}', 'complete', '2025-05-02 16:24:11'),
(297, '_control_read_flag', '{\"purpose\": \"control_read_only\"}', 'complete', '2025-05-02 16:26:04'),
(298, 'read_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:26:04'),
(299, '_control_read_flag', '{}', 'complete', '2025-05-02 16:26:04'),
(300, '_control_read_flag', '{\"purpose\": \"control_read_only\"}', 'complete', '2025-05-02 16:26:22'),
(301, 'read_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:26:22'),
(302, '_control_read_flag', '{}', 'complete', '2025-05-02 16:26:22'),
(303, 'READC', '{\"tag_id\": \"pending\"}', 'complete', '2025-05-02 16:31:17'),
(304, 'READC', '{\"tag_id\": \"pending\"}', 'complete', '2025-05-02 16:33:44'),
(305, 'reset_tag', '{\"control_mode\": true}', 'complete', '2025-05-02 16:34:09'),
(306, 'READC', '{\"tag_id\": \"pending\"}', 'complete', '2025-05-02 16:34:17'),
(307, 'write_tag', '{\"data\": \"Biscuit 250g#4.9\", \"control_mode\": true}', 'complete', '2025-05-02 16:35:20'),
(308, 'READC', '{\"tag_id\": \"pending\"}', 'complete', '2025-05-02 16:35:27'),
(309, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 16:35:36'),
(310, 'LED', '{\"control_mode\": true}', 'complete', '2025-05-02 16:35:38'),
(311, 'BUZZER', '{\"control_mode\": true}', 'complete', '2025-05-02 16:35:40'),
(312, 'open_lid', '{\"product_id\": 20}', 'complete', '2025-05-02 16:36:45'),
(313, 'open_lid', '{\"product_id\": 20}', 'complete', '2025-05-02 16:45:20'),
(314, 'tare', '{}', 'complete', '2025-05-02 16:47:53'),
(315, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:53'),
(316, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:54'),
(317, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:55'),
(318, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:56'),
(319, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:57'),
(320, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:58'),
(321, 'weigh_item', '{}', 'complete', '2025-05-02 16:47:59'),
(322, 'open_lid', '{\"product_id\": 22}', 'complete', '2025-05-26 21:16:23'),
(323, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 21:16:52'),
(324, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:37:13'),
(325, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:37:27'),
(326, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:42:31'),
(327, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:42:47'),
(328, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:48:31'),
(329, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:48:44'),
(330, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:49:01'),
(331, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-26 22:57:02'),
(332, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-29 17:48:43'),
(333, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-29 18:15:23'),
(334, 'open_lid', '{\"product_id\": 3}', 'complete', '2025-05-29 18:15:33');

-- --------------------------------------------------------

--
-- Table structure for table `control_results`
--

CREATE TABLE `control_results` (
  `id` int(11) NOT NULL,
  `tag_id` varchar(100) DEFAULT NULL,
  `data` text DEFAULT NULL,
  `timestamp` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `control_results`
--

INSERT INTO `control_results` (`id`, `tag_id`, `data`, `timestamp`) VALUES
(1, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:13:50'),
(2, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:15:36'),
(3, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:20:17'),
(4, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:37:25'),
(5, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:39:42'),
(6, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 14:48:18'),
(7, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 16:17:00'),
(8, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 16:18:16'),
(9, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 16:19:13'),
(10, 'A971E60D', 'Milk 250ml#2.90', '2025-05-02 16:26:25'),
(11, 'pending', 'Milk 250ml#2.90', '2025-05-02 16:31:18'),
(12, 'pending', 'Milk 250ml#2.90', '2025-05-02 16:33:45'),
(13, 'pending', 'NoData#0', '2025-05-02 16:34:18'),
(14, 'pending', 'Biscuit 250g#4.9', '2025-05-02 16:35:28'),
(15, 'A971E60D', 'Biscuit 250g#4.9', '2025-05-02 16:36:45'),
(16, 'A971E60D', 'Biscuit 250g#4.9', '2025-05-02 16:45:20'),
(17, 'A971E60D', 'Testt#20', '2025-05-26 21:16:23'),
(18, 'A1352C1D', 'nutella 400g#45', '2025-05-26 21:16:52'),
(19, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:37:13'),
(20, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:37:27'),
(21, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:42:31'),
(22, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:42:47'),
(23, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:48:31'),
(24, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:48:44'),
(25, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:49:01'),
(26, 'A1352C1D', 'nutella 400g#45', '2025-05-26 22:57:02'),
(27, 'A1352C1D', 'nutella 400g#45', '2025-05-29 17:48:43'),
(28, 'A1352C1D', 'nutella 400g#45', '2025-05-29 18:15:23'),
(29, 'A1352C1D', 'nutella 400g#45', '2025-05-29 18:15:33');

-- --------------------------------------------------------

--
-- Table structure for table `customers`
--

CREATE TABLE `customers` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `address` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `last_visit` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `customers`
--

INSERT INTO `customers` (`id`, `name`, `address`, `created_at`, `last_visit`) VALUES
(1, 'Shifaz Ahamed', 'Student Village, Kuching', '2025-05-02 09:22:55', '2025-05-29 17:45:15'),
(2, 'Munieb', 'Somewhere in Kuching', '2025-05-02 09:51:02', '2025-05-29 18:15:11'),
(3, 'Mark', 'Saradise', '2025-05-02 13:50:20', '2025-05-26 22:36:59'),
(4, 'John Doe', 'Waterfront', '2025-05-02 14:35:48', '2025-05-26 22:42:12'),
(5, 'Alin', 'Definitely not at uni', '2025-05-26 22:48:10', '2025-05-26 22:56:17');

-- --------------------------------------------------------

--
-- Table structure for table `fraud_logs`
--

CREATE TABLE `fraud_logs` (
  `id` int(11) NOT NULL,
  `event_type` enum('no_placement','multiple_items') NOT NULL,
  `tag_id` varchar(50) DEFAULT NULL,
  `timestamp` datetime DEFAULT current_timestamp(),
  `details` text DEFAULT NULL,
  `session_id` int(11) DEFAULT NULL,
  `synced_to_cloud` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `fraud_logs`
--

INSERT INTO `fraud_logs` (`id`, `event_type`, `tag_id`, `timestamp`, `details`, `session_id`, `synced_to_cloud`) VALUES
(1, '', NULL, '2025-04-30 09:23:52', 'No item placed after scan', NULL, 0),
(2, '', NULL, '2025-04-30 09:25:23', 'No item placed after scan', NULL, 0),
(3, '', NULL, '2025-04-30 09:35:49', 'No item placed after scan', NULL, 0),
(4, '', NULL, '2025-04-30 09:38:54', 'No item placed after scan', NULL, 0),
(5, '', NULL, '2025-04-30 09:42:04', 'No item placed after scan', NULL, 0),
(6, '', NULL, '2025-04-30 09:42:53', 'No item placed after scan', NULL, 0),
(7, '', NULL, '2025-04-30 09:42:55', 'Unscanned product placed', NULL, 0),
(8, '', NULL, '2025-04-30 09:45:38', 'No item placed after scan', NULL, 0),
(9, '', NULL, '2025-05-01 19:26:20', 'Unscanned product placed', NULL, 0),
(10, '', NULL, '2025-05-01 19:26:22', 'Unscanned product placed', NULL, 0),
(11, '', NULL, '2025-05-01 19:26:27', 'Unscanned product placed', NULL, 0),
(12, '', NULL, '2025-05-01 19:26:44', 'No item placed after scan', NULL, 0),
(13, '', NULL, '2025-05-01 19:28:09', 'Multiple items placed after one scan', NULL, 0),
(14, '', NULL, '2025-05-01 19:28:15', 'Unscanned product placed', NULL, 0),
(15, '', NULL, '2025-05-01 19:28:23', 'Unscanned product placed', NULL, 0),
(16, '', NULL, '2025-05-01 19:28:25', 'Unscanned product placed', NULL, 0),
(17, '', NULL, '2025-05-01 19:29:04', 'Multiple items placed after one scan', NULL, 0),
(18, '', NULL, '2025-05-01 19:29:21', 'Unscanned product placed', NULL, 0),
(19, '', NULL, '2025-05-01 19:31:04', 'No item placed after scan', NULL, 0),
(20, '', NULL, '2025-05-02 13:50:02', 'No item placed after scan', NULL, 0),
(21, '', NULL, '2025-05-02 13:53:02', 'No item placed after scan', NULL, 0),
(22, '', NULL, '2025-05-02 14:13:59', 'No item placed after scan', NULL, 0),
(23, '', NULL, '2025-05-02 14:15:31', 'No item placed after scan', NULL, 0),
(24, '', NULL, '2025-05-02 14:20:25', 'No item placed after scan', NULL, 0),
(25, '', NULL, '2025-05-02 14:37:33', 'No item placed after scan', NULL, 0),
(26, '', NULL, '2025-05-02 14:45:10', 'No item placed after scan', NULL, 0),
(27, '', NULL, '2025-05-02 16:17:08', 'No item placed after scan', NULL, 0),
(28, '', NULL, '2025-05-02 16:18:21', 'No item placed after scan', NULL, 0),
(29, '', NULL, '2025-05-02 16:19:27', 'No item placed after scan', NULL, 0),
(30, '', NULL, '2025-05-02 16:26:18', 'No item placed after scan', NULL, 0),
(31, '', NULL, '2025-05-02 16:26:33', 'No item placed after scan', NULL, 0),
(32, '', NULL, '2025-05-02 16:36:36', 'No item placed after scan', NULL, 0),
(33, '', NULL, '2025-05-26 21:17:44', 'Multiple items placed after one scan', NULL, 0),
(34, '', NULL, '2025-05-26 21:17:46', 'Unscanned product placed', NULL, 0),
(35, '', NULL, '2025-05-26 21:17:49', 'Unscanned product placed', NULL, 0),
(36, '', NULL, '2025-05-26 21:17:52', 'Unscanned product placed', NULL, 0),
(37, '', NULL, '2025-05-26 21:17:54', 'Unscanned product placed', NULL, 0),
(38, '', NULL, '2025-05-26 22:37:34', 'No item placed after scan', NULL, 0),
(39, '', NULL, '2025-05-26 22:42:58', 'Multiple items placed after one scan', NULL, 0),
(40, '', NULL, '2025-05-26 22:48:50', 'Multiple items placed after one scan', NULL, 0),
(41, '', NULL, '2025-05-26 22:50:03', 'Multiple items placed after one scan', NULL, 0),
(42, '', NULL, '2025-05-26 22:50:13', 'Unscanned product placed', NULL, 0),
(43, '', NULL, '2025-05-26 22:50:16', 'Unscanned product placed', NULL, 0),
(44, '', NULL, '2025-05-26 22:57:11', 'Multiple items placed after one scan', NULL, 1),
(45, '', NULL, '2025-05-26 23:09:06', 'Unscanned product placed', NULL, 1),
(46, '', NULL, '2025-05-26 23:09:08', 'Unscanned product placed', NULL, 0),
(47, '', NULL, '2025-05-26 23:11:05', 'Unscanned product placed', NULL, 1),
(48, '', NULL, '2025-05-29 17:47:46', 'No item placed after scan', NULL, 1);

-- --------------------------------------------------------

--
-- Table structure for table `grocery_items`
--

CREATE TABLE `grocery_items` (
  `id` int(11) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `price_per_kg` decimal(10,2) NOT NULL,
  `image_path` varchar(255) DEFAULT '/static/images/default.jpg',
  `description` text DEFAULT NULL,
  `is_available` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `grocery_items`
--

INSERT INTO `grocery_items` (`id`, `product_name`, `price_per_kg`, `image_path`, `description`, `is_available`) VALUES
(1, 'Apples', 2.99, '/static/images/apple.jpg', 'Fresh red apples', 1),
(2, 'Bananas', 1.49, '/static/images/banana.jpg', 'Ripe yellow bananas', 1),
(3, 'Oranges', 3.29, '/static/images/orange.jpg', 'Juicy oranges', 1),
(4, 'Tomatoes', 2.49, '/static/images/tomato.jpg', 'Vine-ripened tomatoes', 1),
(5, 'Potatoes', 1.99, '/static/images/potato.jpg', 'Russet potatoes', 1),
(6, 'Carrots', 1.79, '/static/images/carrot.jpg', 'Fresh carrots', 1),
(7, 'Lettuce', 2.99, '/static/images/lettuce.jpg', 'Crisp iceberg lettuce', 1),
(8, 'Onions', 1.29, '/static/images/onion.jpg', 'Yellow onions', 1);

-- --------------------------------------------------------

--
-- Table structure for table `product_data`
--

CREATE TABLE `product_data` (
  `id` int(11) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `is_grocery` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `product_data`
--

INSERT INTO `product_data` (`id`, `product_name`, `price`, `is_grocery`) VALUES
(1, 'cornflakes', 12.00, 0),
(2, 'orange 2kg', 39.00, 0),
(3, 'nutella 400g', 45.00, 0),
(4, 'Milka 75g', 7.65, 0),
(5, 'Apples', 0.05, 1),
(6, 'Onions', 0.04, 1),
(7, 'Apples', 0.04, 1),
(8, 'Milk 250ml', 2.90, 0),
(9, 'Tomatoes', 0.04, 1),
(10, 'Oranges', 0.44, 1),
(11, 'Onions', 0.17, 1),
(12, 'Bananas', 0.03, 1),
(13, 'Tomatoes', 0.08, 1),
(14, 'Onions', 0.08, 1),
(15, 'Carrots', 0.20, 1),
(16, 'Bananas', 0.20, 1),
(17, 'Apples', 0.40, 1),
(18, 'Onions', 0.20, 1),
(19, 'Potatoes', 0.43, 1),
(20, 'Biscuit 250g', 4.90, 0),
(21, 'Tomatoes', 0.07, 1),
(22, 'Testt', 20.00, 0);

-- --------------------------------------------------------

--
-- Table structure for table `scanned_items`
--

CREATE TABLE `scanned_items` (
  `id` int(11) NOT NULL,
  `tag_id` varchar(50) NOT NULL,
  `timestamp` datetime DEFAULT current_timestamp(),
  `product_id` int(11) DEFAULT NULL,
  `weight` decimal(10,2) DEFAULT NULL,
  `is_validated` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `scanned_items`
--

INSERT INTO `scanned_items` (`id`, `tag_id`, `timestamp`, `product_id`, `weight`, `is_validated`) VALUES
(1, 'A971E60D', '2025-04-30 09:23:41', NULL, NULL, 0),
(2, 'A971E60D', '2025-04-30 09:25:03', NULL, NULL, 0),
(3, 'A971E60D', '2025-04-30 09:25:12', NULL, NULL, 0),
(4, 'A971E60D', '2025-04-30 09:35:38', NULL, NULL, 0),
(5, 'A971E60D', '2025-04-30 09:38:43', NULL, NULL, 0),
(6, 'A971E60D', '2025-04-30 09:41:54', NULL, NULL, 0),
(7, 'A971E60D', '2025-04-30 09:42:42', 1, NULL, 0),
(10, 'A971E60D', '2025-04-30 09:45:28', NULL, NULL, 0),
(18, 'A971E60D', '2025-05-01 19:30:54', NULL, NULL, 0),
(20, 'A971E60D', '2025-05-02 13:49:50', NULL, NULL, 0),
(25, 'A971E60D', '2025-05-02 13:52:30', NULL, NULL, 0),
(35, 'A971E60D', '2025-05-02 14:13:48', 8, NULL, 0),
(36, 'A971E60D', '2025-05-02 14:15:19', NULL, NULL, 0),
(37, 'A971E60D', '2025-05-02 14:15:33', 8, NULL, 0),
(38, 'A971E60D', '2025-05-02 14:20:15', 8, NULL, 0),
(39, 'A971E60D', '2025-05-02 14:37:23', 8, NULL, 0),
(40, 'A971E60D', '2025-05-02 14:39:37', 8, NULL, 0),
(41, 'A971E60D', '2025-05-02 14:44:56', NULL, NULL, 0),
(42, 'A971E60D', '2025-05-02 14:45:00', NULL, NULL, 0),
(44, 'A971E60D', '2025-05-02 16:19:15', NULL, NULL, 0),
(45, 'A971E60D', '2025-05-02 16:36:25', NULL, NULL, 0),
(47, 'A971E60D', '2025-05-02 16:44:55', NULL, NULL, 0),
(50, 'A971E60D', '2025-05-26 21:16:18', 22, NULL, 0),
(53, 'A1352C1D', '2025-05-26 22:37:20', NULL, NULL, 0),
(58, 'A1352C1D', '2025-05-26 22:48:41', 3, NULL, 0),
(61, 'A1352C1D', '2025-05-29 17:47:34', NULL, NULL, 0);

-- --------------------------------------------------------

--
-- Table structure for table `shopping_sessions`
--

CREATE TABLE `shopping_sessions` (
  `id` int(11) NOT NULL,
  `customer_id` int(11) DEFAULT NULL,
  `cloud_session_id` varchar(100) DEFAULT NULL,
  `start_time` datetime DEFAULT current_timestamp(),
  `end_time` datetime DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT 0.00,
  `fraud_alerts` int(11) DEFAULT 0,
  `status` enum('active','completed','abandoned') DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `shopping_sessions`
--

INSERT INTO `shopping_sessions` (`id`, `customer_id`, `cloud_session_id`, `start_time`, `end_time`, `total_amount`, `fraud_alerts`, `status`) VALUES
(1, 1, NULL, '2025-05-02 09:22:55', NULL, 0.00, 0, 'active'),
(2, 1, NULL, '2025-05-02 09:31:59', NULL, 0.00, 0, 'active'),
(3, 1, NULL, '2025-05-02 09:35:04', NULL, 0.00, 0, 'active'),
(4, 2, NULL, '2025-05-02 09:51:02', NULL, 0.00, 0, 'active'),
(5, 3, NULL, '2025-05-02 13:50:20', '2025-05-02 13:51:46', 3.55, 0, 'completed'),
(6, 3, NULL, '2025-05-02 13:52:22', '2025-05-02 13:54:02', 4.52, 0, 'completed'),
(7, 3, NULL, '2025-05-02 14:16:11', NULL, 0.00, 0, 'active'),
(8, 4, NULL, '2025-05-02 14:35:48', NULL, 0.00, 0, 'active'),
(9, 1, NULL, '2025-05-02 14:59:21', NULL, 0.00, 0, 'active'),
(10, 2, NULL, '2025-05-02 15:01:23', NULL, 0.00, 0, 'active'),
(11, 1, NULL, '2025-05-02 16:36:07', '2025-05-02 16:36:54', 4.90, 0, 'completed'),
(12, 2, NULL, '2025-05-02 16:44:45', NULL, 0.00, 0, 'active'),
(13, 3, NULL, '2025-05-02 16:47:36', '2025-05-02 16:49:46', 0.07, 0, 'completed'),
(14, 1, NULL, '2025-05-02 16:49:51', NULL, 0.00, 0, 'active'),
(15, 1, NULL, '2025-05-20 19:32:22', NULL, 0.00, 0, 'active'),
(16, 2, NULL, '2025-05-22 00:34:10', '2025-05-22 00:35:50', 2.90, 0, 'completed'),
(17, 1, NULL, '2025-05-22 16:49:26', NULL, 0.00, 0, 'active'),
(18, 4, NULL, '2025-05-22 17:13:53', NULL, 0.00, 0, 'active'),
(19, 1, 'sess_08da7ea3', '2025-05-26 20:21:21', NULL, 0.00, 0, 'active'),
(20, 4, 'sess_b287b74c', '2025-05-26 21:16:10', '2025-05-26 21:17:03', 45.00, 0, 'completed'),
(21, 3, 'sess_62775aac', '2025-05-26 22:37:01', NULL, 0.00, 0, 'active'),
(22, 4, 'sess_414ea804', '2025-05-26 22:42:13', '2025-05-26 22:43:04', 90.00, 0, 'completed'),
(23, 5, 'sess_0b667868', '2025-05-26 22:48:11', '2025-05-26 22:49:15', 90.00, 0, 'completed'),
(24, 5, 'sess_a9a3b0af', '2025-05-26 22:56:17', '2025-05-26 22:57:16', 45.00, 0, 'completed'),
(25, 1, 'sess_9a14a67f', '2025-05-26 23:08:42', NULL, 0.00, 0, 'active'),
(26, 1, 'sess_3a0e4d6a', '2025-05-29 17:45:15', '2025-05-29 17:48:49', 45.00, 0, 'completed'),
(27, 2, 'sess_9caafecb', '2025-05-29 18:15:12', '2025-05-29 18:15:40', 90.00, 0, 'completed');

-- --------------------------------------------------------

--
-- Table structure for table `transactions`
--

CREATE TABLE `transactions` (
  `id` int(11) NOT NULL,
  `user_id` varchar(50) DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT NULL,
  `items` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`items`)),
  `timestamp` datetime DEFAULT current_timestamp(),
  `session_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `transactions`
--

INSERT INTO `transactions` (`id`, `user_id`, `total_amount`, `items`, `timestamp`, `session_id`) VALUES
(1, NULL, 107.04, '[8, 9, 11, 13, 14, 12, 15]', '2025-05-01 19:27:24', NULL),
(2, '1', 10.59, '[16, 17, 19]', '2025-05-01 19:32:33', NULL),
(3, '3', 3.55, '[21, 22, 23, 24]', '2025-05-02 13:51:46', 5),
(4, '3', 4.52, '[26, 27, 28, 29, 30, 31, 32, 33, 34]', '2025-05-02 13:54:02', 6),
(5, '1', 4.90, '[46]', '2025-05-02 16:36:54', 11),
(6, NULL, 4.90, '[48]', '2025-05-02 16:47:30', NULL),
(7, '3', 0.07, '[49]', '2025-05-02 16:49:46', 13),
(8, '2', 2.90, '[43]', '2025-05-22 00:35:50', 16),
(9, '4', 45.00, '[51]', '2025-05-26 21:17:03', 20),
(11, '4', 90.00, '[55, 56]', '2025-05-26 22:43:04', 22),
(12, '5', 90.00, '[57, 59]', '2025-05-26 22:49:15', 23),
(13, '5', 45.00, '[60]', '2025-05-26 22:57:16', 24),
(14, '1', 45.00, '[62]', '2025-05-29 17:48:49', 26),
(15, '2', 90.00, '[63, 64]', '2025-05-29 18:15:40', 27);

-- --------------------------------------------------------

--
-- Table structure for table `weight_readings`
--

CREATE TABLE `weight_readings` (
  `id` int(11) NOT NULL,
  `weight` decimal(10,2) NOT NULL,
  `timestamp` datetime NOT NULL,
  `processed` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `weight_readings`
--

INSERT INTO `weight_readings` (`id`, `weight`, `timestamp`, `processed`) VALUES
(1, 0.01, '2025-04-30 12:22:52', 0),
(2, 0.01, '2025-04-30 12:22:53', 0),
(3, 0.01, '2025-04-30 12:22:55', 0),
(4, 7.72, '2025-04-30 12:22:56', 0),
(5, 15.42, '2025-04-30 12:22:57', 0),
(6, 23.13, '2025-04-30 12:22:58', 0),
(7, 30.84, '2025-04-30 12:22:59', 0),
(8, 0.03, '2025-05-01 19:27:08', 0),
(9, 0.03, '2025-05-01 19:27:09', 0),
(10, 0.03, '2025-05-01 19:27:10', 0),
(11, 0.03, '2025-05-01 19:27:11', 0),
(12, 4.53, '2025-05-01 19:27:12', 0),
(13, 28.03, '2025-05-01 19:27:14', 0),
(14, 50.69, '2025-05-01 19:27:15', 0),
(15, 71.70, '2025-05-01 19:27:16', 0),
(16, 0.04, '2025-05-01 19:29:35', 0),
(17, 0.03, '2025-05-01 19:29:36', 0),
(18, 0.03, '2025-05-01 19:29:37', 0),
(19, 14.96, '2025-05-01 19:29:38', 0),
(20, 29.90, '2025-05-01 19:29:39', 0),
(21, 0.01, '2025-05-02 13:50:53', 0),
(22, 0.01, '2025-05-02 13:50:54', 0),
(23, 0.00, '2025-05-02 13:50:55', 0),
(24, 0.01, '2025-05-02 13:50:56', 0),
(25, 0.01, '2025-05-02 13:50:58', 0),
(26, 0.01, '2025-05-02 13:50:59', 0),
(27, 0.02, '2025-05-02 13:51:00', 0),
(28, 8.40, '2025-05-02 13:51:01', 0),
(29, 16.80, '2025-05-02 13:51:02', 0),
(30, 25.21, '2025-05-02 13:51:04', 0),
(31, 33.62, '2025-05-02 13:51:04', 0),
(32, 134.58, '2025-05-02 13:51:16', 0),
(33, 134.61, '2025-05-02 13:51:17', 0),
(34, 134.63, '2025-05-02 13:51:25', 0),
(35, 0.10, '2025-05-02 13:53:05', 0),
(36, 0.10, '2025-05-02 13:53:06', 0),
(37, 0.11, '2025-05-02 13:53:07', 0),
(38, 0.11, '2025-05-02 13:53:08', 0),
(39, 0.11, '2025-05-02 13:53:09', 0),
(40, 8.58, '2025-05-02 13:53:10', 0),
(41, 17.04, '2025-05-02 13:53:11', 0),
(42, 25.49, '2025-05-02 13:53:12', 0),
(43, 33.94, '2025-05-02 13:53:14', 0),
(44, 42.40, '2025-05-02 13:53:14', 0),
(45, 59.29, '2025-05-02 13:53:16', 0),
(46, 109.93, '2025-05-02 13:53:23', 0),
(47, 135.22, '2025-05-02 13:53:28', 0),
(48, 135.16, '2025-05-02 13:53:30', 0),
(49, 134.62, '2025-05-02 13:53:41', 0),
(50, 153.78, '2025-05-02 13:53:42', 0),
(51, 213.59, '2025-05-02 13:53:45', 0),
(52, 272.52, '2025-05-02 13:53:48', 0),
(53, -0.04, '2025-05-02 14:15:02', 0),
(54, -0.03, '2025-05-02 14:36:27', 0),
(55, 0.01, '2025-05-02 14:39:17', 0),
(56, -0.02, '2025-05-02 14:45:37', 0),
(57, -0.86, '2025-05-02 16:08:41', 0),
(58, 15.41, '2025-05-02 16:16:14', 0),
(59, 123.30, '2025-05-02 16:16:34', 0),
(60, 0.00, '2025-05-02 16:20:26', 0),
(61, -0.02, '2025-05-02 16:22:40', 0),
(62, -0.01, '2025-05-02 16:23:06', 0),
(63, 25.59, '2025-05-02 16:24:12', 0),
(64, 28.81, '2025-05-02 16:47:59', 0),
(65, 33.43, '2025-05-02 16:48:01', 0),
(66, 38.04, '2025-05-02 16:48:01', 0),
(67, 42.66, '2025-05-02 16:48:01', 0),
(68, 47.28, '2025-05-02 16:48:02', 0),
(69, 51.90, '2025-05-02 16:48:02', 0),
(70, 56.52, '2025-05-02 16:48:02', 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `analytics`
--
ALTER TABLE `analytics`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `commands`
--
ALTER TABLE `commands`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `control_results`
--
ALTER TABLE `control_results`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `customers`
--
ALTER TABLE `customers`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `fraud_logs`
--
ALTER TABLE `fraud_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `session_id` (`session_id`);

--
-- Indexes for table `grocery_items`
--
ALTER TABLE `grocery_items`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `product_data`
--
ALTER TABLE `product_data`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `scanned_items`
--
ALTER TABLE `scanned_items`
  ADD PRIMARY KEY (`id`),
  ADD KEY `product_id` (`product_id`);

--
-- Indexes for table `shopping_sessions`
--
ALTER TABLE `shopping_sessions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `customer_id` (`customer_id`);

--
-- Indexes for table `transactions`
--
ALTER TABLE `transactions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `session_id` (`session_id`);

--
-- Indexes for table `weight_readings`
--
ALTER TABLE `weight_readings`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `analytics`
--
ALTER TABLE `analytics`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `commands`
--
ALTER TABLE `commands`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=335;

--
-- AUTO_INCREMENT for table `control_results`
--
ALTER TABLE `control_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- AUTO_INCREMENT for table `customers`
--
ALTER TABLE `customers`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `fraud_logs`
--
ALTER TABLE `fraud_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=49;

--
-- AUTO_INCREMENT for table `grocery_items`
--
ALTER TABLE `grocery_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `product_data`
--
ALTER TABLE `product_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT for table `scanned_items`
--
ALTER TABLE `scanned_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=65;

--
-- AUTO_INCREMENT for table `shopping_sessions`
--
ALTER TABLE `shopping_sessions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=28;

--
-- AUTO_INCREMENT for table `transactions`
--
ALTER TABLE `transactions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT for table `weight_readings`
--
ALTER TABLE `weight_readings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=71;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `fraud_logs`
--
ALTER TABLE `fraud_logs`
  ADD CONSTRAINT `fraud_logs_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`);

--
-- Constraints for table `scanned_items`
--
ALTER TABLE `scanned_items`
  ADD CONSTRAINT `scanned_items_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `product_data` (`id`);

--
-- Constraints for table `shopping_sessions`
--
ALTER TABLE `shopping_sessions`
  ADD CONSTRAINT `shopping_sessions_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`);

--
-- Constraints for table `transactions`
--
ALTER TABLE `transactions`
  ADD CONSTRAINT `transactions_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
