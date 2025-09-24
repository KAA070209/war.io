-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: war_game
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `admins` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `permissions` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT '{}' CHECK (json_valid(`permissions`)),
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admins`
--

LOCK TABLES `admins` WRITE;
/*!40000 ALTER TABLE `admins` DISABLE KEYS */;
INSERT INTO `admins` VALUES (1,'admin','adminpass','{}'),(2,'azka','adminpass','{}');
/*!40000 ALTER TABLE `admins` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `leaderboard`
--

DROP TABLE IF EXISTS `leaderboard`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `leaderboard` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `score` int(11) DEFAULT NULL,
  `kills` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `leaderboard`
--

LOCK TABLES `leaderboard` WRITE;
/*!40000 ALTER TABLE `leaderboard` DISABLE KEYS */;
INSERT INTO `leaderboard` VALUES (1,'azka',3691,193),(2,'Admin',3542,200),(3,'fauzan',2127,97),(4,'leww',1882,74),(5,'alif',595,32),(6,'wamnda',550,35),(7,'Player',131,10),(8,'tes',46,4);
/*!40000 ALTER TABLE `leaderboard` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_data`
--

DROP TABLE IF EXISTS `user_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_data` (
  `user_id` int(11) NOT NULL,
  `coins` int(11) DEFAULT 0,
  `unlocked` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`unlocked`)),
  `upgrades` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`upgrades`)),
  `score` int(11) DEFAULT 0,
  `kills` int(11) DEFAULT 0,
  `weapon` varchar(50) DEFAULT 'pistol',
  `ammo` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`ammo`)),
  PRIMARY KEY (`user_id`),
  CONSTRAINT `user_data_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_data`
--

LOCK TABLES `user_data` WRITE;
/*!40000 ALTER TABLE `user_data` DISABLE KEYS */;
INSERT INTO `user_data` VALUES (1,130143,'[\"flamethrower\", \"time_bomb\", \"freeze_ray\", \"cryo_blaster\", \"grenade\", \"bfg\", \"machinegun\", \"black_hole_gun\", \"flak_cannon\", \"homing_missile\", \"pulse_rifle\", \"laser\", \"plasma\", \"rocket\", \"sword\", \"teleport_gun\", \"chain_lightning\", \"acid_gun\", \"minigun\", \"area_damage\", \"poison_gun\", \"disintegration_ray\", \"shotgun\", \"gravity_gun\", \"gauss_rifle\", \"energy_sword\", \"pistol\", \"lightning_gun\", \"sniper\", \"railgun\", \"napalm_launcher\", \"sonic_blaster\"]','{\"max_hp\": 1, \"speed\": 1, \"dash_cooldown\": 1, \"damage_mult\": 1, \"shield_regen\": 1}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(2,20,'[\"pistol\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999}'),(3,350,'[\"pistol\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(4,400,'[\"machinegun\", \"pistol\", \"shotgun\", \"rocket\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(5,471,'[\"shotgun\", \"minigun\", \"pistol\", \"rocket\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(6,0,'[\"pistol\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(7,0,'[\"pistol\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(8,1020293,'[\"time_bomb\", \"laser\", \"napalm_launcher\", \"rocket\", \"acid_gun\", \"poison_gun\", \"pistol\", \"gauss_rifle\", \"sniper\", \"grenade\", \"gravity_gun\", \"minigun\", \"teleport_gun\", \"lightning_gun\", \"plasma\", \"energy_sword\", \"chain_lightning\", \"railgun\", \"freeze_ray\", \"machinegun\", \"sonic_blaster\", \"cryo_blaster\", \"sword\", \"pulse_rifle\", \"black_hole_gun\", \"area_damage\", \"flamethrower\", \"shotgun\", \"homing_missile\", \"flak_cannon\", \"disintegration_ray\", \"bfg\"]','{\"max_hp\": 1, \"speed\": 1, \"dash_cooldown\": 1, \"shield_regen\": 1, \"damage_mult\": 1}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}'),(10,0,'[\"pistol\"]','{}',0,0,'pistol','{\"pistol\": 999999, \"shotgun\": 30, \"rocket\": 8, \"machinegun\": 150, \"area_damage\": 1, \"sniper\": 12, \"flamethrower\": 80, \"laser\": 40, \"grenade\": 10, \"plasma\": 10, \"sword\": 999999, \"gravity_gun\": 20, \"railgun\": 10, \"minigun\": 200, \"bfg\": 5, \"freeze_ray\": 25, \"poison_gun\": 30, \"lightning_gun\": 15, \"acid_gun\": 20, \"teleport_gun\": 8, \"black_hole_gun\": 6, \"time_bomb\": 12, \"chain_lightning\": 18, \"homing_missile\": 10, \"energy_sword\": 999999, \"flak_cannon\": 25, \"pulse_rifle\": 40, \"gauss_rifle\": 15, \"cryo_blaster\": 20, \"napalm_launcher\": 15, \"sonic_blaster\": 30, \"disintegration_ray\": 8}');
/*!40000 ALTER TABLE `user_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'azka','123'),(2,'novi','123'),(3,'wamnda','123'),(4,'alif','123456'),(5,'fauzan','08882283674bf'),(6,'tes','123'),(7,'radit','123'),(8,'Admin','123'),(10,'admins','password');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-24 14:22:01
