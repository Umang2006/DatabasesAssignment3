CREATE DATABASE  IF NOT EXISTS `dms_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `dms_db`;
-- MySQL dump 10.13  Distrib 8.0.31, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: dms_db
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `member`
--

DROP TABLE IF EXISTS `member`;
CREATE TABLE `member` (
  `member_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `age` int NOT NULL,
  `email` varchar(150) NOT NULL,
  `contact_no` varchar(15) NOT NULL,
  `image` varchar(500) NOT NULL,
  `member_type` varchar(50) NOT NULL,
  PRIMARY KEY (`member_id`),
  UNIQUE KEY `email` (`email`),
  CONSTRAINT `member_chk_1` CHECK ((`age` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `member` WRITE;
/*!40000 ALTER TABLE `member` DISABLE KEYS */;
INSERT INTO `member` VALUES
(1,'Amit Sharma',30,'amit@gmail.com','9876543210','https://img.com/1.jpg','Patient'),
(2,'Riya Patel',25,'riya@gmail.com','9876543211','https://img.com/2.jpg','Patient'),
(3,'Karan Mehta',40,'karan@gmail.com','9876543212','https://img.com/3.jpg','Doctor'),
(4,'Neha Singh',38,'neha@gmail.com','9876543213','https://img.com/4.jpg','Doctor'),
(5,'Rahul Verma',29,'rahul@gmail.com','9876543214','https://img.com/5.jpg','Staff'),
(6,'Pooja Jain',32,'pooja@gmail.com','9876543215','https://img.com/6.jpg','Staff'),
(7,'Arjun Rao',45,'arjun@gmail.com','9876543216','https://img.com/7.jpg','Doctor'),
(8,'Sneha Iyer',28,'sneha@gmail.com','9876543217','https://img.com/8.jpg','Patient'),
(9,'Vikas Nair',35,'vikas@gmail.com','9876543218','https://img.com/9.jpg','Doctor'),
(10,'Meera Das',31,'meera@gmail.com','9876543219','https://img.com/10.jpg','Staff'),
(11,'Rohan Shah',27,'rohan@gmail.com','9876543220','https://img.com/11.jpg','Patient'),
(12,'Anjali Roy',33,'anjali@gmail.com','9876543221','https://img.com/12.jpg','Staff'),
(13,'Deepak Kumar',42,'deepak@gmail.com','9876543222','https://img.com/13.jpg','Doctor'),
(14,'Simran Kaur',26,'simran@gmail.com','9876543223','https://img.com/14.jpg','Patient'),
(15,'Manish Gupta',50,'manish@gmail.com','9876543224','https://img.com/15.jpg','Staff');
/*!40000 ALTER TABLE `member` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int DEFAULT NULL,
  `username` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `role` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
(1,1,'amit','$2b$12$swJFtbwadJ8nuhxb56SOreSgnQw9rIWxAi.AKQLzUBlCwXYunTjIm','user'),
(5,3,'admin','$2b$12$swJFtbwadJ8nuhxb56SOreSgnQw9rIWxAi.AKQLzUBlCwXYunTjIm','admin');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `member_group_mapping`
--

DROP TABLE IF EXISTS `member_group_mapping`;
CREATE TABLE `member_group_mapping` (
  `mapping_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `group_name` varchar(100) NOT NULL,
  `assigned_role` varchar(50) NOT NULL,
  PRIMARY KEY (`mapping_id`),
  KEY `idx_mgm_member_id` (`member_id`),
  CONSTRAINT `mgm_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `member_group_mapping` WRITE;
/*!40000 ALTER TABLE `member_group_mapping` DISABLE KEYS */;
INSERT INTO `member_group_mapping` (member_id, group_name, assigned_role) VALUES
(1,'Patients','Patient'),
(2,'Patients','Patient'),
(3,'Doctors','Doctor'),
(4,'Doctors','Doctor'),
(5,'Staff','Staff'),
(6,'Staff','Staff'),
(7,'Doctors','Doctor'),
(8,'Patients','Patient'),
(9,'Doctors','Doctor'),
(10,'Staff','Staff'),
(11,'Patients','Patient'),
(12,'Staff','Staff'),
(13,'Doctors','Doctor'),
(14,'Patients','Patient'),
(15,'Staff','Staff');
/*!40000 ALTER TABLE `member_group_mapping` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `doctor`
--

DROP TABLE IF EXISTS `doctor`;
CREATE TABLE `doctor` (
  `doctor_id` int NOT NULL AUTO_INCREMENT,
  `specialization` varchar(100) NOT NULL,
  `qualification` varchar(100) NOT NULL,
  `consultation_fee` int NOT NULL,
  `salary` int NOT NULL,
  `shift` varchar(50) NOT NULL,
  `member_id` int NOT NULL,
  PRIMARY KEY (`doctor_id`),
  UNIQUE KEY `member_id` (`member_id`),
  CONSTRAINT `doctor_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `doctor_chk_1` CHECK ((`consultation_fee` >= 0)),
  CONSTRAINT `doctor_chk_2` CHECK ((`salary` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `doctor` WRITE;
/*!40000 ALTER TABLE `doctor` DISABLE KEYS */;
INSERT INTO `doctor` VALUES
(1,'Cardiologist','MD',800,90000,'Morning',3),
(2,'Dermatologist','MBBS',600,80000,'Evening',4),
(3,'Neurologist','MD',1000,120000,'Morning',7),
(4,'Orthopedic','MS',900,110000,'Evening',9),
(5,'Pediatrician','MD',700,85000,'Morning',13);
/*!40000 ALTER TABLE `doctor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `patient`
--

DROP TABLE IF EXISTS `patient`;
CREATE TABLE `patient` (
  `patient_id` int NOT NULL AUTO_INCREMENT,
  `blood_group` varchar(5) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `address` varchar(255) NOT NULL,
  `member_id` int NOT NULL,
  PRIMARY KEY (`patient_id`),
  UNIQUE KEY `member_id` (`member_id`),
  CONSTRAINT `patient_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `patient` WRITE;
/*!40000 ALTER TABLE `patient` DISABLE KEYS */;
INSERT INTO `patient` VALUES
(1,'O+','Male','Delhi',1),
(2,'A+','Female','Mumbai',2),
(3,'B+','Female','Chennai',8),
(4,'AB+','Male','Kolkata',11),
(5,'O-','Female','Jaipur',14);
/*!40000 ALTER TABLE `patient` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `nonmedicalstaff`
--

DROP TABLE IF EXISTS `nonmedicalstaff`;
CREATE TABLE `nonmedicalstaff` (
  `staff_id` int NOT NULL AUTO_INCREMENT,
  `role` varchar(100) NOT NULL,
  `salary` int NOT NULL,
  `shift` varchar(50) NOT NULL,
  `member_id` int NOT NULL,
  PRIMARY KEY (`staff_id`),
  UNIQUE KEY `member_id` (`member_id`),
  CONSTRAINT `nonmedicalstaff_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `nonmedicalstaff_chk_1` CHECK ((`salary` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `nonmedicalstaff` WRITE;
/*!40000 ALTER TABLE `nonmedicalstaff` DISABLE KEYS */;
INSERT INTO `nonmedicalstaff` VALUES
(1,'Receptionist',30000,'Morning',5),
(2,'Pharmacist',35000,'Evening',6),
(3,'Billing Clerk',28000,'Morning',10),
(4,'Store Manager',40000,'Evening',12),
(5,'Helper',20000,'Morning',15);
/*!40000 ALTER TABLE `nonmedicalstaff` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `medicine`
--

DROP TABLE IF EXISTS `medicine`;
CREATE TABLE `medicine` (
  `medicine_id` int NOT NULL AUTO_INCREMENT,
  `medicine_name` varchar(150) NOT NULL,
  `manufacturer` varchar(150) NOT NULL,
  `price` int NOT NULL,
  `category` varchar(100) NOT NULL,
  PRIMARY KEY (`medicine_id`),
  CONSTRAINT `medicine_chk_1` CHECK ((`price` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `medicine` WRITE;
/*!40000 ALTER TABLE `medicine` DISABLE KEYS */;
INSERT INTO `medicine` VALUES
(1,'Paracetamol','Cipla',50,'Fever'),
(2,'Aspirin','Sun Pharma',40,'Pain'),
(3,'Amoxicillin','Mankind',120,'Antibiotic'),
(4,'Ibuprofen','Dr Reddy',80,'Pain'),
(5,'Cetirizine','Zydus',30,'Allergy'),
(6,'Metformin','Lupin',100,'Diabetes'),
(7,'Atorvastatin','Cipla',150,'Cholesterol'),
(8,'Azithromycin','Sun Pharma',200,'Antibiotic'),
(9,'Pantoprazole','Mankind',90,'Acidity'),
(10,'Vitamin D','Dr Reddy',60,'Supplement');
/*!40000 ALTER TABLE `medicine` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `inventory`
--

DROP TABLE IF EXISTS `inventory`;
CREATE TABLE `inventory` (
  `inventory_id` int NOT NULL AUTO_INCREMENT,
  `manufacturing_date` date NOT NULL,
  `expiry_date` date NOT NULL,
  `quantity` int NOT NULL,
  `medicine_id` int NOT NULL,
  PRIMARY KEY (`inventory_id`),
  KEY `medicine_id` (`medicine_id`),
  CONSTRAINT `inventory_ibfk_1` FOREIGN KEY (`medicine_id`) REFERENCES `medicine` (`medicine_id`),
  CONSTRAINT `inventory_chk_1` CHECK ((`quantity` >= 0)),
  CONSTRAINT `inventory_chk_2` CHECK ((`expiry_date` > `manufacturing_date`))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `inventory` WRITE;
/*!40000 ALTER TABLE `inventory` DISABLE KEYS */;
INSERT INTO `inventory` VALUES
(1,'2024-01-01','2026-01-01',200,1),
(2,'2024-02-01','2026-02-01',150,2),
(3,'2024-03-01','2026-03-01',100,3),
(4,'2024-04-01','2026-04-01',120,4),
(5,'2024-05-01','2026-05-01',180,5),
(6,'2024-06-01','2026-06-01',220,6),
(7,'2024-07-01','2026-07-01',140,7),
(8,'2024-08-01','2026-08-01',160,8),
(9,'2024-09-01','2026-09-01',130,9),
(10,'2024-10-01','2026-10-01',170,10);
/*!40000 ALTER TABLE `inventory` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `slots`
--

DROP TABLE IF EXISTS `slots`;
CREATE TABLE `slots` (
  `slot_id` int NOT NULL AUTO_INCREMENT,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'Available',
  `doctor_id` int NOT NULL,
  PRIMARY KEY (`slot_id`),
  KEY `doctor_id` (`doctor_id`),
  CONSTRAINT `slots_ibfk_1` FOREIGN KEY (`doctor_id`) REFERENCES `doctor` (`doctor_id`) ON DELETE CASCADE,
  CONSTRAINT `slots_chk_1` CHECK ((`end_time` > `start_time`))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `slots` WRITE;
/*!40000 ALTER TABLE `slots` DISABLE KEYS */;
INSERT INTO `slots` VALUES
(1,'09:00:00','09:30:00','Available',1),
(2,'09:30:00','10:00:00','Booked',1),
(3,'10:00:00','10:30:00','Available',2),
(4,'10:30:00','11:00:00','Booked',2),
(5,'11:00:00','11:30:00','Available',3),
(6,'11:30:00','12:00:00','Booked',3),
(7,'14:00:00','14:30:00','Available',4),
(8,'14:30:00','15:00:00','Booked',4),
(9,'15:00:00','15:30:00','Available',5),
(10,'15:30:00','16:00:00','Booked',5);
/*!40000 ALTER TABLE `slots` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `appointment`
--

DROP TABLE IF EXISTS `appointment`;
CREATE TABLE `appointment` (
  `appointment_id` int NOT NULL AUTO_INCREMENT,
  `appointment_date` date NOT NULL,
  `appointment_time` time NOT NULL,
  `doctor_id` int NOT NULL,
  `patient_id` int NOT NULL,
  `slot_id` int NOT NULL,
  PRIMARY KEY (`appointment_id`),
  KEY `patient_id` (`patient_id`),
  KEY `slot_id` (`slot_id`),
  KEY `idx_appointment_doctor` (`doctor_id`),
  CONSTRAINT `appointment_ibfk_1` FOREIGN KEY (`doctor_id`) REFERENCES `doctor` (`doctor_id`),
  CONSTRAINT `appointment_ibfk_2` FOREIGN KEY (`patient_id`) REFERENCES `patient` (`patient_id`),
  CONSTRAINT `appointment_ibfk_3` FOREIGN KEY (`slot_id`) REFERENCES `slots` (`slot_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `appointment` WRITE;
/*!40000 ALTER TABLE `appointment` DISABLE KEYS */;
INSERT INTO `appointment` VALUES
(1,'2025-03-01','09:30:00',1,1,2),
(2,'2025-03-02','10:30:00',2,2,4),
(3,'2025-03-03','11:30:00',3,3,6),
(4,'2025-03-04','14:30:00',4,4,8),
(5,'2025-03-05','15:30:00',5,5,10),
(6,'2025-03-06','09:00:00',1,2,1),
(7,'2025-03-07','10:00:00',2,1,3),
(8,'2025-03-08','11:00:00',3,4,5),
(9,'2025-03-09','14:00:00',4,3,7),
(10,'2025-03-10','15:00:00',5,5,9),
(11,'2026-04-01','10:00:00',3,1,1);
/*!40000 ALTER TABLE `appointment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `prescription`
--

DROP TABLE IF EXISTS `prescription`;
CREATE TABLE `prescription` (
  `prescription_id` int NOT NULL AUTO_INCREMENT,
  `appointment_id` int NOT NULL,
  PRIMARY KEY (`prescription_id`),
  UNIQUE KEY `appointment_id` (`appointment_id`),
  CONSTRAINT `prescription_ibfk_1` FOREIGN KEY (`appointment_id`) REFERENCES `appointment` (`appointment_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `prescription` WRITE;
/*!40000 ALTER TABLE `prescription` DISABLE KEYS */;
INSERT INTO `prescription` VALUES (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10);
/*!40000 ALTER TABLE `prescription` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `prescription_details`
--

DROP TABLE IF EXISTS `prescription_details`;
CREATE TABLE `prescription_details` (
  `prescription_id` int NOT NULL,
  `medicine_id` int NOT NULL,
  `dosage` varchar(100) NOT NULL,
  `duration` int NOT NULL,
  PRIMARY KEY (`prescription_id`,`medicine_id`),
  KEY `medicine_id` (`medicine_id`),
  CONSTRAINT `prescription_details_ibfk_1` FOREIGN KEY (`prescription_id`) REFERENCES `prescription` (`prescription_id`) ON DELETE CASCADE,
  CONSTRAINT `prescription_details_ibfk_2` FOREIGN KEY (`medicine_id`) REFERENCES `medicine` (`medicine_id`),
  CONSTRAINT `prescription_details_chk_1` CHECK ((`duration` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `prescription_details` WRITE;
/*!40000 ALTER TABLE `prescription_details` DISABLE KEYS */;
INSERT INTO `prescription_details` VALUES
(1,1,'500mg',5),(1,2,'75mg',3),(2,3,'250mg',7),(2,4,'400mg',4),(3,2,'75mg',2),
(3,4,'400mg',5),(4,3,'250mg',6),(4,5,'10mg',10),(5,5,'10mg',8),(5,6,'500mg',30),
(6,7,'20mg',15),(7,8,'250mg',5),(8,9,'40mg',7),(9,10,'1000IU',30),(10,1,'500mg',3);
/*!40000 ALTER TABLE `prescription_details` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bill`
--

DROP TABLE IF EXISTS `bill`;
CREATE TABLE `bill` (
  `bill_id` int NOT NULL AUTO_INCREMENT,
  `amount` int NOT NULL,
  `bill_date` date NOT NULL,
  `appointment_id` int NOT NULL,
  PRIMARY KEY (`bill_id`),
  UNIQUE KEY `appointment_id` (`appointment_id`),
  CONSTRAINT `bill_ibfk_1` FOREIGN KEY (`appointment_id`) REFERENCES `appointment` (`appointment_id`) ON DELETE CASCADE,
  CONSTRAINT `bill_chk_1` CHECK ((`amount` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

LOCK TABLES `bill` WRITE;
/*!40000 ALTER TABLE `bill` DISABLE KEYS */;
INSERT INTO `bill` VALUES
(1,500,'2025-03-01',1),(2,600,'2025-03-02',2),(3,700,'2025-03-03',3),
(4,800,'2025-03-04',4),(5,900,'2025-03-05',5),(6,400,'2025-03-06',6),
(7,650,'2025-03-07',7),(8,750,'2025-03-08',8),(9,550,'2025-03-09',9),
(10,950,'2025-03-10',10);
/*!40000 ALTER TABLE `bill` ENABLE KEYS */;
UNLOCK TABLES;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-22
