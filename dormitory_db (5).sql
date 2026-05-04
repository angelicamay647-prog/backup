-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: May 04, 2026 at 10:45 AM
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
-- Database: `dormitory_db`
--

DELIMITER $$
--
-- Procedures
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_admin_dashboard_summary` ()   BEGIN
    SELECT COUNT(*) AS total_renters FROM renters WHERE renter_status = 'Active';
    SELECT room_number, floor_level, occupied, capacity, available_slots, status
    FROM vw_room_occupancy_summary ORDER BY room_number;
    SELECT renter_name, invoice_number, billing_month, amount, balance_amount, status, days_since_due
    FROM vw_overdue_payments ORDER BY days_since_due DESC;
    SELECT request_id, room_number, renter_name, issue, priority, status, request_date
    FROM vw_maintenance_full WHERE status = 'Pending'
    ORDER BY FIELD(priority,'High','Medium','Low'), request_date ASC;
    SELECT actor_role, actor_name, action_type, action_text, log_timestamp
    FROM vw_activity_log_full ORDER BY log_timestamp DESC LIMIT 20;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_assign_renter_to_room` (IN `p_renter_id` INT, IN `p_room_id` INT, IN `p_bed` VARCHAR(50), IN `p_check_in` DATE, IN `p_rate` DECIMAL(10,2), IN `p_admin_id` INT, OUT `p_result_msg` VARCHAR(200))   BEGIN
    DECLARE v_capacity INT DEFAULT 0;
    DECLARE v_occupied INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; SET p_result_msg = 'ERROR: Assignment failed.'; END;

    SELECT capacity, occupied INTO v_capacity, v_occupied FROM rooms WHERE room_id = p_room_id;
    IF v_occupied >= v_capacity THEN
        SET p_result_msg = 'ERROR: Room is already at full capacity.';
    ELSE
        START TRANSACTION;
            INSERT INTO assignments (renter_id, room_id, bed_assignment, check_in_date, agreed_rate, assigned_by)
            VALUES (p_renter_id, p_room_id, p_bed, p_check_in, p_rate, p_admin_id);
            UPDATE rooms SET occupied = occupied + 1 WHERE room_id = p_room_id;
            INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
            VALUES (p_admin_id, 'ASSIGN',
                    CONCAT('Renter ID ', p_renter_id, ' assigned to room ', p_room_id, ' — bed: ', p_bed),
                    'Admin');
        COMMIT;
        SET p_result_msg = CONCAT('SUCCESS: Renter ', p_renter_id, ' assigned to room ', p_room_id);
    END IF;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_checkout_renter` (IN `p_renter_id` INT, IN `p_admin_id` INT, IN `p_checkout_date` DATE, OUT `p_result_msg` VARCHAR(200))   BEGIN
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; SET p_result_msg = 'ERROR: Checkout failed.'; END;

    START TRANSACTION;
        SELECT room_id INTO v_room_id FROM assignments
        WHERE renter_id = p_renter_id AND status = 'Active' LIMIT 1;
        UPDATE assignments SET status = 'Checked Out', check_out_date = p_checkout_date
        WHERE  renter_id = p_renter_id AND status = 'Active';
        UPDATE renters SET renter_status = 'Inactive' WHERE renter_id = p_renter_id;
        UPDATE renter_accounts SET account_status = 'Inactive' WHERE renter_id = p_renter_id;
        IF v_room_id IS NOT NULL THEN
            UPDATE rooms SET occupied = GREATEST(occupied - 1, 0) WHERE room_id = v_room_id;
        END IF;
        INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
        VALUES (p_admin_id, 'CHECKOUT',
                CONCAT('Renter ID ', p_renter_id, ' checked out on ', p_checkout_date),
                'Admin');
    COMMIT;
    SET p_result_msg = CONCAT('SUCCESS: Renter ', p_renter_id, ' checked out.');
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_login` (IN `p_username` VARCHAR(50), IN `p_password` VARCHAR(255), OUT `p_role` VARCHAR(20), OUT `p_display_name` VARCHAR(100), OUT `p_ref_id` INT, OUT `p_success` TINYINT(1))   BEGIN
    DECLARE v_admin_id  INT DEFAULT NULL;
    DECLARE v_acct_id   INT DEFAULT NULL;
    DECLARE v_renter_id INT DEFAULT NULL;
    DECLARE v_role      VARCHAR(20);
    DECLARE v_name      VARCHAR(100);

    SET p_success = 0;

    -- Check admins table (Admin + Staff share this table)
    SELECT admin_id, role, full_name
    INTO v_admin_id, v_role, v_name
    FROM admins
    WHERE username = p_username AND password = p_password
    LIMIT 1;

    IF v_admin_id IS NOT NULL THEN
        SET p_role         = v_role;
        SET p_display_name = v_name;
        SET p_ref_id       = v_admin_id;
        SET p_success      = 1;

        -- Update last_login
        UPDATE admins SET last_login = NOW() WHERE admin_id = v_admin_id;

        -- Log the action
        INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
        VALUES (v_admin_id, 'LOGIN', CONCAT(v_name, ' logged in as ', v_role), v_role);

    ELSE
        -- Check renter_accounts
        SELECT ra.account_id, ra.renter_id,
               CONCAT(r.first_name,' ',r.last_name)
        INTO v_acct_id, v_renter_id, v_name
        FROM renter_accounts ra
        JOIN renters r ON ra.renter_id = r.renter_id
        WHERE ra.username = p_username
          AND ra.password = p_password
          AND ra.account_status = 'Active'
        LIMIT 1;

        IF v_acct_id IS NOT NULL THEN
            SET p_role         = 'Renter';
            SET p_display_name = v_name;
            SET p_ref_id       = v_renter_id;
            SET p_success      = 1;

            -- Update last_login
            UPDATE renter_accounts SET last_login = NOW() WHERE account_id = v_acct_id;

            -- Log the action
            INSERT INTO activity_logs (renter_id, action_type, action_text, actor_role)
            VALUES (v_acct_id, 'LOGIN', CONCAT(v_name, ' (Renter) logged in'), 'Renter');
        END IF;
    END IF;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_log_action` (IN `p_admin_id` INT, IN `p_renter_id` INT, IN `p_role` VARCHAR(20), IN `p_action_type` VARCHAR(50), IN `p_action_text` VARCHAR(255))   BEGIN
    INSERT INTO activity_logs (admin_id, renter_id, action_type, action_text, actor_role)
    VALUES (p_admin_id, p_renter_id, p_action_type, p_action_text, p_role);
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_record_payment` (IN `p_invoice_number` VARCHAR(50), IN `p_renter_id` INT, IN `p_amount` DECIMAL(10,2), IN `p_balance` DECIMAL(10,2), IN `p_method` VARCHAR(30), IN `p_reference` VARCHAR(100), IN `p_billing_month` VARCHAR(20), IN `p_payment_date` DATE, IN `p_due_date` DATE, IN `p_status` VARCHAR(20), IN `p_remarks` TEXT, IN `p_processed_by` INT, OUT `p_result_msg` VARCHAR(200))   proc_body: BEGIN
    DECLARE v_exists INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; SET p_result_msg = 'ERROR: Transaction rolled back.'; END;

    SELECT COUNT(*) INTO v_exists FROM renters WHERE renter_id = p_renter_id;
    IF v_exists = 0 THEN SET p_result_msg = 'ERROR: Renter not found.'; LEAVE proc_body; END IF;

    SELECT COUNT(*) INTO v_exists FROM payments WHERE invoice_number = p_invoice_number;
    IF v_exists > 0 THEN SET p_result_msg = 'ERROR: Invoice number already exists.'; LEAVE proc_body; END IF;

    START TRANSACTION;
        INSERT INTO payments (invoice_number, renter_id, amount, balance_amount, payment_method,
            reference_number, billing_month, payment_date, due_date, status, remarks, processed_by)
        VALUES (p_invoice_number, p_renter_id, p_amount, p_balance, p_method,
            p_reference, p_billing_month, p_payment_date, p_due_date, p_status, p_remarks, p_processed_by);
        INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
        VALUES (p_processed_by, 'PAYMENT',
                CONCAT('Payment recorded: Invoice ', p_invoice_number, ' — P', p_amount, ' (', p_status, ')'),
                'Admin');
    COMMIT;
    SET p_result_msg = CONCAT('SUCCESS: Payment recorded for Invoice ', p_invoice_number);
END proc_body$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_renter_dashboard` (IN `p_renter_id` INT)   BEGIN
    -- Result Set 1: Profile + Room
    SELECT
        fn_full_name(r.first_name, r.middle_name, r.last_name) AS full_name,
        r.email, r.contact_number, r.renter_status,
        fn_get_room_of_renter(r.renter_id)  AS room_number,
        asn.bed_assignment,
        asn.check_in_date,
        asn.agreed_rate,
        fn_get_renter_balance(r.renter_id)  AS outstanding_balance
    FROM renters r
    LEFT JOIN assignments asn ON asn.renter_id = r.renter_id AND asn.status = 'Active'
    WHERE r.renter_id = p_renter_id;

    -- Result Set 2: Payment history (transparency)
    SELECT
        invoice_number, billing_month, amount, balance_amount,
        payment_method, payment_date,
        fn_payment_label(status) AS status_label,
        payment_summary
    FROM vw_renter_payment_transparency
    WHERE renter_id = p_renter_id
    ORDER BY payment_date DESC;

    -- Result Set 3: Utility bills for their room
    SELECT
        bill_type, billing_month, amount_per_person,
        total_bill_amount, consumption,
        billing_date, due_date, bill_status
    FROM vw_renter_utility_bills
    WHERE room_id = (
        SELECT room_id FROM assignments
        WHERE renter_id = p_renter_id AND status = 'Active'
        LIMIT 1
    )
    ORDER BY billing_date DESC;

    -- Result Set 4: Maintenance requests they submitted
    SELECT
        request_id, room_number, issue, priority,
        status, request_date, completion_date, resolution_notes
    FROM vw_maintenance_full
    WHERE renter_id = p_renter_id
    ORDER BY request_date DESC;
END$$

CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_submit_maintenance` (IN `p_room_id` INT, IN `p_renter_id` INT, IN `p_description` TEXT, IN `p_priority` VARCHAR(10), IN `p_actor_role` VARCHAR(20), IN `p_actor_id` INT, OUT `p_result_msg` VARCHAR(200))   BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; SET p_result_msg = 'ERROR: Could not submit maintenance request.'; END;

    START TRANSACTION;
        INSERT INTO maintenance_requests (room_id, renter_id, description, priority)
        VALUES (p_room_id, p_renter_id, p_description, p_priority);
        IF p_actor_role = 'Renter' THEN
            INSERT INTO activity_logs (renter_id, action_type, action_text, actor_role)
            VALUES (p_actor_id, 'MAINTENANCE',
                    CONCAT('Submitted maintenance request: ', LEFT(p_description,80)), 'Renter');
        ELSE
            INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
            VALUES (p_actor_id, 'MAINTENANCE',
                    CONCAT('Logged maintenance request for room ', p_room_id), p_actor_role);
        END IF;
    COMMIT;
    SET p_result_msg = 'SUCCESS: Maintenance request submitted.';
END$$

--
-- Functions
--
CREATE DEFINER=`root`@`localhost` FUNCTION `fn_days_overdue` (`p_payment_date` DATE) RETURNS INT(11) DETERMINISTIC NO SQL BEGIN
    RETURN DATEDIFF(CURDATE(), p_payment_date);
END$$

CREATE DEFINER=`root`@`localhost` FUNCTION `fn_full_name` (`p_first` VARCHAR(50), `p_middle` VARCHAR(50), `p_last` VARCHAR(50)) RETURNS VARCHAR(150) CHARSET utf8mb4 COLLATE utf8mb4_general_ci DETERMINISTIC NO SQL BEGIN
    RETURN TRIM(CONCAT(
        COALESCE(p_first,''), ' ',
        CASE WHEN p_middle IS NOT NULL AND p_middle != ''
             THEN CONCAT(p_middle,' ') ELSE '' END,
        COALESCE(p_last,'')
    ));
END$$

CREATE DEFINER=`root`@`localhost` FUNCTION `fn_get_renter_balance` (`p_renter_id` INT) RETURNS DECIMAL(10,2) DETERMINISTIC READS SQL DATA BEGIN
    DECLARE v_balance DECIMAL(10,2) DEFAULT 0.00;
    SELECT COALESCE(SUM(balance_amount), 0.00)
    INTO   v_balance
    FROM   payments
    WHERE  renter_id = p_renter_id
      AND  status IN ('Pending','Partial','Overdue');
    RETURN v_balance;
END$$

CREATE DEFINER=`root`@`localhost` FUNCTION `fn_get_room_of_renter` (`p_renter_id` INT) RETURNS VARCHAR(10) CHARSET utf8mb4 COLLATE utf8mb4_general_ci DETERMINISTIC READS SQL DATA BEGIN
    DECLARE v_room VARCHAR(10) DEFAULT 'Unassigned';
    SELECT rm.room_number INTO v_room
    FROM   assignments asn
    JOIN   rooms rm ON asn.room_id = rm.room_id
    WHERE  asn.renter_id = p_renter_id
      AND  asn.status = 'Active'
    LIMIT  1;
    RETURN v_room;
END$$

CREATE DEFINER=`root`@`localhost` FUNCTION `fn_payment_label` (`p_status` VARCHAR(20)) RETURNS VARCHAR(60) CHARSET utf8mb4 COLLATE utf8mb4_general_ci DETERMINISTIC NO SQL BEGIN
    RETURN CASE p_status
        WHEN 'Paid'     THEN 'Fully Paid'
        WHEN 'Partial'  THEN 'Partial - Balance Remaining'
        WHEN 'Pending'  THEN 'Pending Payment'
        WHEN 'Overdue'  THEN 'OVERDUE'
        WHEN 'Advanced' THEN 'Advanced Payment'
        ELSE 'Unknown'
    END;
END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `activity_logs`
--

CREATE TABLE `activity_logs` (
  `log_id` int(11) NOT NULL,
  `admin_id` int(11) DEFAULT NULL,
  `action_type` varchar(50) DEFAULT NULL,
  `action_text` varchar(255) DEFAULT NULL,
  `log_timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `staff_id` int(11) DEFAULT NULL COMMENT 'links to admins where role=Staff',
  `renter_id` int(11) DEFAULT NULL COMMENT 'links to renter_accounts',
  `actor_role` varchar(20) DEFAULT 'Admin' COMMENT 'Admin | Staff | Renter'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `activity_logs`
--

INSERT INTO `activity_logs` (`log_id`, `admin_id`, `action_type`, `action_text`, `log_timestamp`, `staff_id`, `renter_id`, `actor_role`) VALUES
(1, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:39:45', NULL, NULL, 'Admin'),
(2, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:39:45', NULL, NULL, 'Admin'),
(3, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:39:45', NULL, NULL, 'Admin'),
(4, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:42:34', NULL, NULL, 'Admin'),
(5, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:42:34', NULL, NULL, 'Admin'),
(6, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:42:34', NULL, NULL, 'Admin'),
(7, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:55:00', NULL, NULL, 'Admin'),
(8, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 02:55:00', NULL, NULL, 'Admin'),
(9, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 03:44:40', NULL, NULL, 'Admin'),
(10, 2, 'LOGIN', 'Patrick Rodriguez logged in.', '2026-04-26 03:45:45', NULL, NULL, 'Admin'),
(11, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 03:53:19', NULL, NULL, 'Admin'),
(12, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 03:54:09', NULL, NULL, 'Admin'),
(13, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 03:57:26', NULL, NULL, 'Admin'),
(14, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 04:10:48', NULL, NULL, 'Admin'),
(15, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-26 04:32:52', NULL, NULL, 'Admin'),
(16, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-29 08:05:21', NULL, NULL, 'Admin'),
(17, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-04-29 08:06:51', NULL, NULL, 'Admin'),
(18, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-30 01:47:30', NULL, NULL, 'Admin'),
(19, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-30 03:50:12', NULL, NULL, 'Admin'),
(20, 3, 'LOGIN', 'Jefferson Lagrisola logged in.', '2026-04-30 03:54:39', NULL, NULL, 'Admin'),
(21, 3, 'LOGOUT', 'Jefferson Lagrisola logged out.', '2026-04-30 04:19:24', NULL, NULL, 'Admin'),
(22, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-04-30 04:19:37', NULL, NULL, 'Admin'),
(23, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-02 08:56:00', NULL, NULL, 'Admin'),
(24, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-02 09:06:13', NULL, NULL, 'Admin'),
(25, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-02 09:07:06', NULL, NULL, 'Admin'),
(26, 3, 'LOGIN', 'Jefferson Lagrisola logged in.', '2026-05-02 09:07:18', NULL, NULL, 'Staff'),
(27, 3, 'LOGOUT', 'Jefferson Lagrisola logged out.', '2026-05-02 09:09:17', NULL, NULL, 'Admin'),
(28, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-02 09:22:39', NULL, NULL, 'Admin'),
(29, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-02 09:23:07', NULL, NULL, 'Admin'),
(30, 3, 'LOGIN', 'Jefferson Lagrisola logged in.', '2026-05-02 09:23:20', NULL, NULL, 'Staff'),
(31, 3, 'VISITOR_IN', 'Marj Adoptante logged in as visitor', '2026-05-02 09:35:24', NULL, NULL, 'Admin'),
(32, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-02 15:21:59', NULL, NULL, 'Admin'),
(33, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-03 05:32:54', NULL, NULL, 'Admin'),
(34, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-03 05:33:45', NULL, NULL, 'Admin'),
(35, 3, 'LOGIN', 'Jefferson Lagrisola logged in.', '2026-05-03 05:34:04', NULL, NULL, 'Staff'),
(36, 3, 'LOGOUT', 'Jefferson Lagrisola logged out.', '2026-05-03 05:36:03', NULL, NULL, 'Admin'),
(37, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-03 05:36:28', NULL, NULL, 'Admin'),
(38, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-03 05:36:41', NULL, NULL, 'Admin'),
(39, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-03 19:23:24', NULL, NULL, 'Admin'),
(40, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-04 05:44:15', NULL, NULL, 'Admin'),
(41, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-04 05:44:36', NULL, NULL, 'Admin'),
(42, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-04 05:56:30', NULL, NULL, 'Admin'),
(43, 1, 'REJECT_APPLICATION', 'Rejected application from Heeseung Batumbakal.', '2026-05-04 05:57:14', NULL, NULL, 'Admin'),
(44, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-04 05:58:07', NULL, NULL, 'Admin'),
(45, 1, 'LOGIN', 'Angelica May Albarda logged in.', '2026-05-04 05:58:16', NULL, NULL, 'Admin'),
(46, 1, 'LOGOUT', 'Angelica May Albarda logged out.', '2026-05-04 05:58:58', NULL, NULL, 'Admin');

-- --------------------------------------------------------

--
-- Table structure for table `admins`
--

CREATE TABLE `admins` (
  `admin_id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `full_name` varchar(100) DEFAULT NULL,
  `role` varchar(20) DEFAULT 'Admin',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  `monthly_salary` decimal(10,2) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `contact_number` varchar(30) DEFAULT NULL,
  `profile_pic_path` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `admins`
--

INSERT INTO `admins` (`admin_id`, `username`, `password`, `full_name`, `role`, `created_at`, `last_login`, `monthly_salary`, `email`, `contact_number`, `profile_pic_path`) VALUES
(1, 'gel_admin', 'fac8408337d57da1f7ac65b47ced33687f5c3fe164b7729c8860d71125e1810a', 'Angelica May Albarda', 'Admin', '2026-04-24 05:37:09', NULL, NULL, NULL, NULL, NULL),
(2, 'staff_pat', '10176e7b7b24d317acfcf8d2064cfd2f24e154f7b5a96603077d5ef813d6a6b6', 'Patrick Rodriguez', 'Staff', '2026-04-24 05:54:29', NULL, NULL, NULL, NULL, NULL),
(3, 'jeff_staff', 'b5e1ab528f3310f41d458f5df18a60a584d0fa96d51554fe34f139900dc17972', 'Jefferson Lagrisola', 'Staff', '2026-04-24 06:16:43', NULL, NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `assignments`
--

CREATE TABLE `assignments` (
  `assignment_id` int(11) NOT NULL,
  `renter_id` int(11) DEFAULT NULL,
  `room_id` int(11) DEFAULT NULL,
  `bed_assignment` varchar(50) DEFAULT NULL,
  `check_in_date` date DEFAULT NULL,
  `check_out_date` date DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Active',
  `security_deposit` decimal(10,2) DEFAULT 0.00,
  `contract_term` varchar(50) DEFAULT NULL,
  `initial_electric_reading` int(11) DEFAULT 0,
  `assigned_by` int(11) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `agreed_rate` decimal(10,2) DEFAULT 1800.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `assignments`
--

INSERT INTO `assignments` (`assignment_id`, `renter_id`, `room_id`, `bed_assignment`, `check_in_date`, `check_out_date`, `status`, `security_deposit`, `contract_term`, `initial_electric_reading`, `assigned_by`, `notes`, `created_at`, `agreed_rate`) VALUES
(1, 1, 1, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:04', 1800.00),
(2, 2, 1, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:04', 1800.00),
(3, 3, 2, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:13', 1800.00),
(4, 4, 2, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:13', 1800.00),
(5, 5, 3, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:25', 1800.00),
(6, 6, 3, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:25', 1800.00),
(7, 7, 4, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:38', 1800.00),
(8, 8, 4, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:38', 1800.00),
(9, 9, 5, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:51', 1800.00),
(10, 10, 5, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:51', 1800.00),
(11, 11, 5, 'Bed B - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:51', 1800.00),
(12, 12, 5, 'Bed B - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:51', 1800.00),
(13, 13, 5, 'Bed C - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:54:51', 1800.00),
(14, 14, 6, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:55:03', 1800.00),
(15, 15, 6, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:55:03', 1800.00),
(16, 16, 6, 'Bed B - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:55:03', 1800.00),
(17, 17, 7, 'Bed A - Bottom', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:55:25', 1800.00),
(18, 18, 7, 'Bed A - Top', '2026-04-25', NULL, 'Active', 0.00, NULL, 0, NULL, NULL, '2026-04-25 12:55:25', 1800.00);

--
-- Triggers `assignments`
--
DELIMITER $$
CREATE TRIGGER `trg_room_occupancy_add` AFTER INSERT ON `assignments` FOR EACH ROW BEGIN
    IF NEW.status = 'Active' THEN
        UPDATE rooms SET occupied = occupied + 1 WHERE room_id = NEW.room_id;
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `trg_room_occupancy_remove` AFTER UPDATE ON `assignments` FOR EACH ROW BEGIN
    IF OLD.status = 'Active' AND NEW.status != 'Active' THEN
        UPDATE rooms SET occupied = GREATEST(occupied - 1, 0) WHERE room_id = NEW.room_id;
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `facility_overview`
--

CREATE TABLE `facility_overview` (
  `facility_id` int(11) NOT NULL,
  `floor_level` varchar(20) DEFAULT NULL,
  `facility_type` varchar(50) DEFAULT NULL,
  `count` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `facility_overview`
--

INSERT INTO `facility_overview` (`facility_id`, `floor_level`, `facility_type`, `count`) VALUES
(1, 'Ground Floor', 'Bathroom (Flush-type Bowl)', 2),
(2, 'Ground Floor', 'WiFi Router (Dedicated)', 2),
(3, 'Second Floor', 'Bathroom (Flush-type Bowl & Shower Head)', 1),
(4, 'Second Floor', 'WiFi Router (Dedicated)', 1);

-- --------------------------------------------------------

--
-- Table structure for table `maintenance`
--

CREATE TABLE `maintenance` (
  `request_id` int(11) NOT NULL,
  `room_id` int(11) DEFAULT NULL,
  `requester_renter_id` int(11) DEFAULT NULL,
  `issue` text DEFAULT NULL,
  `priority_level` enum('Low','Medium','High') DEFAULT 'Medium',
  `request_date` date DEFAULT NULL,
  `completion_date` date DEFAULT NULL,
  `status` enum('Pending','In Progress','Resolved','Cancelled') DEFAULT 'Pending',
  `resolution_notes` text DEFAULT NULL,
  `assigned_staff_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `maintenance_requests`
--

CREATE TABLE `maintenance_requests` (
  `request_id` int(11) NOT NULL,
  `room_id` int(11) DEFAULT NULL,
  `renter_id` int(11) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `priority` enum('Low','Medium','High') DEFAULT 'Medium',
  `status` enum('Pending','In Progress','Completed') DEFAULT 'Pending',
  `request_date` timestamp NOT NULL DEFAULT current_timestamp(),
  `resolution_notes` text DEFAULT NULL,
  `completion_date` date DEFAULT NULL,
  `resolved_date` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Triggers `maintenance_requests`
--
DELIMITER $$
CREATE TRIGGER `trg_auto_log_maintenance` AFTER INSERT ON `maintenance_requests` FOR EACH ROW BEGIN
    INSERT INTO activity_logs (action_type, action_text, actor_role)
    VALUES (
        'MAINTENANCE',
        CONCAT('New maintenance request #', NEW.request_id,
               ' for room_id ', NEW.room_id, ' — Priority: ', NEW.priority),
        'System'
    );
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `payment_id` int(11) NOT NULL,
  `invoice_number` varchar(50) DEFAULT NULL,
  `renter_id` int(11) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `balance_amount` decimal(10,2) DEFAULT 0.00,
  `payment_method` enum('Cash','GCash','Bank Transfer','Other') DEFAULT 'Cash',
  `reference_number` varchar(100) DEFAULT NULL,
  `billing_month` varchar(20) DEFAULT NULL,
  `payment_date` date DEFAULT curdate(),
  `status` enum('Paid','Partial','Pending','Overdue','Advanced') DEFAULT 'Pending',
  `processed_by` int(11) DEFAULT NULL,
  `remarks` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Triggers `payments`
--
DELIMITER $$
CREATE TRIGGER `trg_auto_log_payment` AFTER INSERT ON `payments` FOR EACH ROW BEGIN
    INSERT INTO activity_logs (admin_id, action_type, action_text, actor_role)
    VALUES (
        NEW.processed_by,
        'PAYMENT',
        CONCAT('Payment inserted: Invoice ', NEW.invoice_number,
               ' — ₱', NEW.amount, ' — Status: ', NEW.status),
        'System'
    );
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `rental_applications`
--

CREATE TABLE `rental_applications` (
  `application_id` int(11) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `gender` varchar(20) DEFAULT 'Other',
  `occupation_type` varchar(50) DEFAULT 'Student',
  `institution` varchar(200) DEFAULT NULL,
  `contact_number` varchar(30) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `emergency_name` varchar(150) DEFAULT NULL,
  `emergency_number` varchar(30) DEFAULT NULL,
  `preferred_room` varchar(100) DEFAULT NULL,
  `message` text DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Pending',
  `submitted_at` datetime DEFAULT current_timestamp(),
  `reviewed_at` datetime DEFAULT NULL,
  `reviewed_by` int(11) DEFAULT NULL,
  `rejection_reason` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rental_applications`
--

INSERT INTO `rental_applications` (`application_id`, `first_name`, `last_name`, `gender`, `occupation_type`, `institution`, `contact_number`, `email`, `address`, `emergency_name`, `emergency_number`, `preferred_room`, `message`, `status`, `submitted_at`, `reviewed_at`, `reviewed_by`, `rejection_reason`) VALUES
(1, 'Heeseung', 'Batumbakal', 'Male', 'Student', 'Rather not say', '09123456789', 'heeseung@gmail.com', 'Agoncillo, Lemery, Batangas', 'Vice Ganda', '09987654321', 'Floor 1', '', 'Rejected', '2026-05-04 13:56:17', '2026-05-04 13:57:14', 1, 'sorry');

-- --------------------------------------------------------

--
-- Table structure for table `renters`
--

CREATE TABLE `renters` (
  `renter_id` int(11) NOT NULL,
  `first_name` varchar(50) DEFAULT NULL,
  `middle_name` varchar(50) DEFAULT NULL,
  `last_name` varchar(50) DEFAULT NULL,
  `occupation_type` enum('Student','Professional','Other') DEFAULT 'Student',
  `institution_employer` varchar(100) DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `contact_number` varchar(15) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `id_type` varchar(50) DEFAULT NULL,
  `id_number` varchar(50) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `emergency_contact_name` varchar(100) DEFAULT NULL,
  `emergency_contact_number` varchar(15) DEFAULT NULL,
  `date_registered` date DEFAULT curdate(),
  `renter_status` enum('Active','Inactive','Blacklisted') DEFAULT 'Active',
  `profile_pic_path` varchar(255) DEFAULT 'default.png'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `renters`
--

INSERT INTO `renters` (`renter_id`, `first_name`, `middle_name`, `last_name`, `occupation_type`, `institution_employer`, `gender`, `contact_number`, `email`, `id_type`, `id_number`, `address`, `emergency_contact_name`, `emergency_contact_number`, `date_registered`, `renter_status`, `profile_pic_path`) VALUES
(1, 'Gianna Hope', 'M.', 'Umali', 'Student', NULL, 'Female', '09001010001', 'gianna@email.com', 'School ID', '22-01234', 'Brgy. Bagong Pook, Lemery, Batangas', 'Rachel Umali', '09171234567', '2026-04-25', 'Active', 'default.png'),
(2, 'Maria Christina', 'A.', 'Bautista', 'Student', NULL, 'Female', '09001010002', 'maria@email.com', 'School ID', '22-05678', 'Agoncillo, Lemery,  Batangas', 'Fe Bautista', '09187654321', '2026-04-25', 'Active', 'default.png'),
(3, 'Cherey', 'J.', 'Bobadilla', 'Student', NULL, 'Female', '09001020001', 'cherey@email.com', 'School ID', '22-09876', 'San Nicolas, Batangas', 'Cheche Bobadilla', '09201112222', '2026-04-25', 'Active', 'default.png'),
(4, 'Hazel', '', 'Mendoza', 'Student', NULL, 'Female', '09001020002', 'hazel@email.com', 'National ID', '1002-8877-6655', 'Lemery, Batangas', 'Marvin Mendoza', '09213334444', '2026-04-25', 'Active', 'default.png'),
(5, 'Marjorie', 'C.', 'Adoptante', 'Student', NULL, 'Female', '09002010001', 'marjorie@email.com', 'School ID', '22-03344', 'Bilaran, Nasugbu, Batangas', 'Marj. Adoptante', '09335556666', '2026-04-25', 'Active', 'default.png'),
(6, 'Valentina', 'D.', 'Aquino', 'Student', NULL, 'Female', '09002010002', 'valentina@email.com', 'School ID', '22-07788', 'San Isidro, Lemery, Batangas', 'Ehly Aquino', '09447778888', '2026-04-25', 'Active', 'default.png'),
(7, 'Zita', '', 'Hernandez', 'Student', NULL, 'Female', '09002020001', 'zita@email.com', 'National ID', '1234-5678-9012', 'Ibaan, Batangas', 'Maria. Hernandez', '09551112222', '2026-04-25', 'Active', 'default.png'),
(8, 'Kat', '', 'Arada', 'Student', NULL, 'Female', '09002020002', 'kat@email.com', 'School ID', '22-04455', 'Balayan, Batangas', 'Kathy. Arada', '09663334444', '2026-04-25', 'Active', 'default.png'),
(9, 'Jessica', '', 'Julongbayan', 'Student', NULL, 'Female', '09002030001', 'jessica@email.com', 'School ID', '22-09111', 'Balayan, Batangas', 'Jess. Julongbayan', '09771112222', '2026-04-25', 'Active', 'default.png'),
(10, 'Reynalyn', '', 'Condicion', 'Student', NULL, 'Female', '09002030002', 'reynalyn@email.com', 'School ID', '24-6908', 'Pantalan, Nasugbu, Batangas', 'Rey. Condicion', '09882223333', '2026-04-25', 'Active', 'default.png'),
(11, 'Gwyneth', 'M.', 'Dimalaluan', 'Student', NULL, 'Female', '09002030003', 'gwyneth@email.com', 'School ID', '22-01122', 'Balayan, Batangas', 'Gwy. Dimalaluan', '09993334444', '2026-04-25', 'Active', 'default.png'),
(12, 'Lyka', 'D.', 'Lopez', 'Student', NULL, 'Female', '09002030004', 'lyka@email.com', 'Postal ID', 'P99-88-776', 'Balayan, Batangas', 'Kyle. Lopez', '09004445555', '2026-04-25', 'Active', 'default.png'),
(13, 'Kyla', 'D.', 'Lopez', 'Student', NULL, 'Female', '09002030005', 'kyla@email.com', 'School ID', '22-03322', 'Balayan, Batangas', 'Kyle. Lopez', '09115556666', '2026-04-25', 'Active', 'default.png'),
(14, 'Jairah', '', 'Endaya', 'Student', NULL, 'Female', '09002040001', 'jairah@email.com', 'School ID', '22-04411', 'San Isidro, Lemery, Batangas', 'Jai Endaya', '09226667777', '2026-04-25', 'Active', 'default.png'),
(15, 'Khyla', '', 'Mercado', 'Student', NULL, 'Female', '09002040002', 'khyla@email.com', 'National ID', '2233-4455-6677', 'Calaca, Batangas', 'Kai. Mercado', '09338889999', '2026-04-25', 'Active', 'default.png'),
(16, 'Monique', '', 'Castillo', 'Student', NULL, 'Female', '09002040003', 'monique@email.com', 'School ID', '22-06655', 'Tuy, Batangas', 'Ryzza. Castillo', '09441112222', '2026-04-25', 'Active', 'default.png'),
(17, 'Enzel', '', 'Sarmiento', 'Student', NULL, 'Female', '09002050001', 'enzel@email.com', 'School ID', '22-05511', 'Tuy, Batangas', 'Frances. Sarmiento', '09553334444', '2026-04-25', 'Active', 'default.png'),
(18, 'Kylie', '', 'Mercado', 'Student', NULL, 'Female', '09002050002', 'kylie@email.com', 'National ID', '3344-5566-7788', 'Calaca, Batangas', 'Kai. Mercado', '09669990000', '2026-04-25', 'Active', 'default.png');

--
-- Triggers `renters`
--
DELIMITER $$
CREATE TRIGGER `trg_renter_account_on_insert` AFTER INSERT ON `renters` FOR EACH ROW BEGIN
    INSERT IGNORE INTO renter_accounts (renter_id, username, password, account_status)
    VALUES (
        NEW.renter_id,
        CONCAT('renter', NEW.renter_id),
        '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2',
        'Active'
    );
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `trg_sync_renter_account_status` AFTER UPDATE ON `renters` FOR EACH ROW BEGIN
    IF NEW.renter_status IN ('Inactive','Blacklisted')
       AND OLD.renter_status = 'Active' THEN
        UPDATE renter_accounts
        SET    account_status = 'Inactive'
        WHERE  renter_id = NEW.renter_id;
    ELSEIF NEW.renter_status = 'Active'
       AND OLD.renter_status != 'Active' THEN
        UPDATE renter_accounts
        SET    account_status = 'Active'
        WHERE  renter_id = NEW.renter_id;
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `renter_accounts`
--

CREATE TABLE `renter_accounts` (
  `account_id` int(11) NOT NULL,
  `renter_id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL DEFAULT 'dorm123',
  `account_status` enum('Active','Inactive') DEFAULT 'Active',
  `last_login` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `renter_accounts`
--

INSERT INTO `renter_accounts` (`account_id`, `renter_id`, `username`, `password`, `account_status`, `last_login`) VALUES
(1, 1, 'renter1', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(2, 2, 'renter2', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(3, 3, 'renter3', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(4, 4, 'renter4', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(5, 5, 'renter5', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(6, 6, 'renter6', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(7, 7, 'renter7', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(8, 8, 'renter8', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(9, 9, 'renter9', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(10, 10, 'renter10', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(11, 11, 'renter11', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(12, 12, 'renter12', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(13, 13, 'renter13', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(14, 14, 'renter14', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(15, 15, 'renter15', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(16, 16, 'renter16', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(17, 17, 'renter17', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL),
(18, 18, 'renter18', '61df1e9e1259222baa127bf0fde5bfc78aec3cf954f015a452ebfb388968dcb2', 'Active', NULL);

--
-- Triggers `renter_accounts`
--
DELIMITER $$
CREATE TRIGGER `trg_update_last_login_renter` BEFORE UPDATE ON `renter_accounts` FOR EACH ROW BEGIN
    IF NEW.last_login IS NOT NULL AND OLD.last_login IS NULL THEN
        SET NEW.last_login = NOW();
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `rooms`
--

CREATE TABLE `rooms` (
  `room_id` int(11) NOT NULL,
  `room_number` varchar(10) DEFAULT NULL,
  `floor_level` enum('1st Floor','2nd Floor') DEFAULT '1st Floor',
  `monthly_rate` decimal(10,2) DEFAULT NULL,
  `capacity` int(11) DEFAULT NULL,
  `occupied` int(11) DEFAULT 0,
  `status` enum('Available','Full','Under Maintenance') DEFAULT 'Available',
  `description` varchar(255) DEFAULT NULL,
  `photo_path` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `rooms`
--

INSERT INTO `rooms` (`room_id`, `room_number`, `floor_level`, `monthly_rate`, `capacity`, `occupied`, `status`, `description`, `photo_path`) VALUES
(1, '101', '1st Floor', 1800.00, 4, 2, 'Available', 'Near the bathroom', NULL),
(2, '102', '1st Floor', 1800.00, 6, 2, 'Available', 'In the corner', NULL),
(3, '201', '2nd Floor', 1800.00, 6, 2, 'Available', 'Near the balcony', NULL),
(4, '202', '2nd Floor', 1800.00, 4, 2, 'Available', 'Near the balcony', NULL),
(5, '203', '2nd Floor', 1800.00, 8, 5, 'Available', 'In the middle', NULL),
(6, '204', '2nd Floor', 1800.00, 4, 3, 'Available', 'At the very corner near the bathroom and living room', NULL),
(7, '205', '2nd Floor', 1800.00, 4, 2, 'Available', 'Near the kitchen', NULL);

--
-- Triggers `rooms`
--
DELIMITER $$
CREATE TRIGGER `trg_room_status_before_update` BEFORE UPDATE ON `rooms` FOR EACH ROW BEGIN
    IF NEW.status != 'Under Maintenance' THEN
        IF NEW.occupied >= NEW.capacity THEN
            SET NEW.status = 'Full';
        ELSEIF NEW.occupied < NEW.capacity AND NEW.status = 'Full' THEN
            SET NEW.status = 'Available';
        END IF;
    END IF;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `trg_room_status_update` AFTER UPDATE ON `rooms` FOR EACH ROW BEGIN
    IF NEW.occupied >= NEW.capacity AND NEW.status != 'Under Maintenance' THEN
        UPDATE rooms SET status = 'Full' WHERE room_id = NEW.room_id;
    ELSEIF NEW.occupied < NEW.capacity AND NEW.status = 'Full' THEN
        UPDATE rooms SET status = 'Available' WHERE room_id = NEW.room_id;
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `room_amenities`
--

CREATE TABLE `room_amenities` (
  `amenity_id` int(11) NOT NULL,
  `room_id` int(11) DEFAULT NULL,
  `amenity_name` varchar(100) DEFAULT NULL,
  `quantity` int(11) DEFAULT 1,
  `item_condition` enum('Good','Needs Repair','Replaced') DEFAULT 'Good'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_amenities`
--

INSERT INTO `room_amenities` (`amenity_id`, `room_id`, `amenity_name`, `quantity`, `item_condition`) VALUES
(1, 1, 'High-Speed WiFi Access', 1, 'Good'),
(2, 1, 'Water Supply (All-in)', 1, 'Good'),
(3, 1, 'Electricity (All-in)', 1, 'Good');

-- --------------------------------------------------------

--
-- Table structure for table `staff_payroll`
--

CREATE TABLE `staff_payroll` (
  `payroll_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `period_month` varchar(20) NOT NULL COMMENT 'e.g. May 2026',
  `basic_salary` decimal(10,2) DEFAULT 0.00,
  `allowances` decimal(10,2) DEFAULT 0.00,
  `deductions` decimal(10,2) DEFAULT 0.00,
  `net_pay` decimal(10,2) DEFAULT 0.00,
  `payment_date` date DEFAULT NULL,
  `payment_method` varchar(30) DEFAULT 'Cash',
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `utility_bills`
--

CREATE TABLE `utility_bills` (
  `bill_id` int(11) NOT NULL,
  `room_id` int(11) DEFAULT NULL,
  `bill_type` enum('Electricity','Water','Internet','Others') DEFAULT 'Electricity',
  `previous_reading` decimal(10,2) DEFAULT NULL,
  `current_reading` decimal(10,2) DEFAULT NULL,
  `consumption` decimal(10,2) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `amount_per_person` decimal(10,2) DEFAULT NULL,
  `billing_month` varchar(20) DEFAULT NULL,
  `billing_date` date DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `payment_date` date DEFAULT NULL,
  `status` enum('Unpaid','Paid') DEFAULT 'Unpaid',
  `reference_no` varchar(50) DEFAULT NULL,
  `payment_proof` varchar(255) DEFAULT NULL,
  `date_recorded` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `visitor_logs`
--

CREATE TABLE `visitor_logs` (
  `visitor_id` int(11) NOT NULL,
  `renter_id` int(11) DEFAULT NULL,
  `visitor_name` varchar(100) DEFAULT NULL,
  `relationship` varchar(50) DEFAULT NULL,
  `time_in` datetime DEFAULT current_timestamp(),
  `time_out` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `visitor_logs`
--

INSERT INTO `visitor_logs` (`visitor_id`, `renter_id`, `visitor_name`, `relationship`, `time_in`, `time_out`) VALUES
(1, 5, 'Marj Adoptante', 'Parent', '2026-05-02 17:35:24', '2026-05-02 17:35:44');

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_activity_log_full`
-- (See below for the actual view)
--
CREATE TABLE `vw_activity_log_full` (
`log_id` int(11)
,`actor_role` varchar(20)
,`actor_name` varchar(101)
,`action_type` varchar(50)
,`action_text` varchar(255)
,`log_timestamp` timestamp
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_all_users`
-- (See below for the actual view)
--
CREATE TABLE `vw_all_users` (
`user_id` int(11)
,`username` varchar(50)
,`password` varchar(255)
,`role` varchar(20)
,`display_name` varchar(101)
,`source_table` varchar(6)
,`renter_id` int(11)
,`account_status` varchar(8)
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_maintenance_full`
-- (See below for the actual view)
--
CREATE TABLE `vw_maintenance_full` (
`request_id` int(11)
,`room_id` int(11)
,`room_number` varchar(10)
,`renter_id` int(11)
,`renter_name` varchar(101)
,`issue` text
,`priority` enum('Low','Medium','High')
,`status` enum('Pending','In Progress','Completed')
,`request_date` timestamp
,`completion_date` date
,`resolution_notes` text
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_overdue_payments`
-- (See below for the actual view)
--
CREATE TABLE `vw_overdue_payments` (
`payment_id` int(11)
,`renter_id` int(11)
,`renter_name` varchar(101)
,`invoice_number` varchar(50)
,`billing_month` varchar(20)
,`amount` decimal(10,2)
,`balance_amount` decimal(10,2)
,`status` enum('Paid','Partial','Pending','Overdue','Advanced')
,`payment_date` date
,`days_since_due` int(7)
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_renter_payment_transparency`
-- (See below for the actual view)
--
CREATE TABLE `vw_renter_payment_transparency` (
`payment_id` int(11)
,`renter_id` int(11)
,`renter_name` varchar(101)
,`invoice_number` varchar(50)
,`billing_month` varchar(20)
,`amount` decimal(10,2)
,`balance_amount` decimal(10,2)
,`payment_method` enum('Cash','GCash','Bank Transfer','Other')
,`reference_number` varchar(100)
,`payment_date` date
,`status` enum('Paid','Partial','Pending','Overdue','Advanced')
,`remarks` text
,`processed_by_name` varchar(100)
,`payment_summary` varchar(31)
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_renter_profile_full`
-- (See below for the actual view)
--
CREATE TABLE `vw_renter_profile_full` (
`renter_id` int(11)
,`full_name` varchar(150)
,`gender` varchar(10)
,`occupation_type` enum('Student','Professional','Other')
,`institution_employer` varchar(100)
,`contact_number` varchar(15)
,`email` varchar(100)
,`renter_status` enum('Active','Inactive','Blacklisted')
,`date_registered` date
,`username` varchar(50)
,`account_status` enum('Active','Inactive')
,`last_login` datetime
,`room_id` int(11)
,`room_number` varchar(10)
,`floor_level` enum('1st Floor','2nd Floor')
,`bed_assignment` varchar(50)
,`check_in_date` date
,`agreed_rate` decimal(10,2)
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_renter_utility_bills`
-- (See below for the actual view)
--
CREATE TABLE `vw_renter_utility_bills` (
`bill_id` int(11)
,`room_id` int(11)
,`room_number` varchar(10)
,`bill_type` enum('Electricity','Water','Internet','Others')
,`billing_month` varchar(20)
,`previous_reading` decimal(10,2)
,`current_reading` decimal(10,2)
,`consumption` decimal(10,2)
,`total_bill_amount` decimal(10,2)
,`amount_per_person` decimal(10,2)
,`billing_date` date
,`due_date` date
,`bill_status` enum('Unpaid','Paid')
,`payment_date` date
);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_room_occupancy_summary`
-- (See below for the actual view)
--
CREATE TABLE `vw_room_occupancy_summary` (
`room_id` int(11)
,`room_number` varchar(10)
,`floor_level` enum('1st Floor','2nd Floor')
,`capacity` int(11)
,`occupied` int(11)
,`available_slots` bigint(12)
,`status` enum('Available','Full','Under Maintenance')
,`monthly_rate` decimal(10,2)
,`photo_path` varchar(255)
);

-- --------------------------------------------------------

--
-- Structure for view `vw_activity_log_full`
--
DROP TABLE IF EXISTS `vw_activity_log_full`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_activity_log_full`  AS SELECT `l`.`log_id` AS `log_id`, `l`.`actor_role` AS `actor_role`, coalesce(`a`.`full_name`,concat(`r`.`first_name`,' ',`r`.`last_name`),'System') AS `actor_name`, `l`.`action_type` AS `action_type`, `l`.`action_text` AS `action_text`, `l`.`log_timestamp` AS `log_timestamp` FROM ((`activity_logs` `l` left join `admins` `a` on(`l`.`admin_id` = `a`.`admin_id`)) left join `renters` `r` on(`l`.`renter_id` = `r`.`renter_id`)) ;

-- --------------------------------------------------------

--
-- Structure for view `vw_all_users`
--
DROP TABLE IF EXISTS `vw_all_users`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_all_users`  AS SELECT `a`.`admin_id` AS `user_id`, `a`.`username` AS `username`, `a`.`password` AS `password`, `a`.`role` AS `role`, `a`.`full_name` AS `display_name`, 'admin' AS `source_table`, NULL AS `renter_id`, 'Active' AS `account_status` FROM `admins` AS `a`union all select `ra`.`account_id` AS `user_id`,`ra`.`username` AS `username`,`ra`.`password` AS `password`,'Renter' AS `role`,concat(`r`.`first_name`,' ',`r`.`last_name`) AS `display_name`,'renter' AS `source_table`,`ra`.`renter_id` AS `renter_id`,`ra`.`account_status` AS `account_status` from (`renter_accounts` `ra` join `renters` `r` on(`ra`.`renter_id` = `r`.`renter_id`))  ;

-- --------------------------------------------------------

--
-- Structure for view `vw_maintenance_full`
--
DROP TABLE IF EXISTS `vw_maintenance_full`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_maintenance_full`  AS SELECT `mr`.`request_id` AS `request_id`, `mr`.`room_id` AS `room_id`, `rm`.`room_number` AS `room_number`, `mr`.`renter_id` AS `renter_id`, concat(`r`.`first_name`,' ',`r`.`last_name`) AS `renter_name`, `mr`.`description` AS `issue`, `mr`.`priority` AS `priority`, `mr`.`status` AS `status`, `mr`.`request_date` AS `request_date`, `mr`.`resolved_date` AS `completion_date`, `mr`.`resolution_notes` AS `resolution_notes` FROM ((`maintenance_requests` `mr` join `rooms` `rm` on(`mr`.`room_id` = `rm`.`room_id`)) join `renters` `r` on(`mr`.`renter_id` = `r`.`renter_id`)) ;

-- --------------------------------------------------------

--
-- Structure for view `vw_overdue_payments`
--
DROP TABLE IF EXISTS `vw_overdue_payments`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_overdue_payments`  AS SELECT `p`.`payment_id` AS `payment_id`, `p`.`renter_id` AS `renter_id`, concat(`r`.`first_name`,' ',`r`.`last_name`) AS `renter_name`, `p`.`invoice_number` AS `invoice_number`, `p`.`billing_month` AS `billing_month`, `p`.`amount` AS `amount`, `p`.`balance_amount` AS `balance_amount`, `p`.`status` AS `status`, `p`.`payment_date` AS `payment_date`, to_days(curdate()) - to_days(`p`.`payment_date`) AS `days_since_due` FROM (`payments` `p` join `renters` `r` on(`p`.`renter_id` = `r`.`renter_id`)) WHERE `p`.`status` in ('Overdue','Pending') ;

-- --------------------------------------------------------

--
-- Structure for view `vw_renter_payment_transparency`
--
DROP TABLE IF EXISTS `vw_renter_payment_transparency`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_renter_payment_transparency`  AS SELECT `p`.`payment_id` AS `payment_id`, `p`.`renter_id` AS `renter_id`, concat(`r`.`first_name`,' ',`r`.`last_name`) AS `renter_name`, `p`.`invoice_number` AS `invoice_number`, `p`.`billing_month` AS `billing_month`, `p`.`amount` AS `amount`, `p`.`balance_amount` AS `balance_amount`, `p`.`payment_method` AS `payment_method`, `p`.`reference_number` AS `reference_number`, `p`.`payment_date` AS `payment_date`, `p`.`status` AS `status`, `p`.`remarks` AS `remarks`, `a`.`full_name` AS `processed_by_name`, concat(`p`.`billing_month`,' — ',`p`.`status`) AS `payment_summary` FROM ((`payments` `p` join `renters` `r` on(`p`.`renter_id` = `r`.`renter_id`)) left join `admins` `a` on(`p`.`processed_by` = `a`.`admin_id`)) ;

-- --------------------------------------------------------

--
-- Structure for view `vw_renter_profile_full`
--
DROP TABLE IF EXISTS `vw_renter_profile_full`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_renter_profile_full`  AS SELECT `r`.`renter_id` AS `renter_id`, `fn_full_name`(`r`.`first_name`,`r`.`middle_name`,`r`.`last_name`) AS `full_name`, `r`.`gender` AS `gender`, `r`.`occupation_type` AS `occupation_type`, `r`.`institution_employer` AS `institution_employer`, `r`.`contact_number` AS `contact_number`, `r`.`email` AS `email`, `r`.`renter_status` AS `renter_status`, `r`.`date_registered` AS `date_registered`, `ra`.`username` AS `username`, `ra`.`account_status` AS `account_status`, `ra`.`last_login` AS `last_login`, `asn`.`room_id` AS `room_id`, `rm`.`room_number` AS `room_number`, `rm`.`floor_level` AS `floor_level`, `asn`.`bed_assignment` AS `bed_assignment`, `asn`.`check_in_date` AS `check_in_date`, `asn`.`agreed_rate` AS `agreed_rate` FROM (((`renters` `r` left join `renter_accounts` `ra` on(`r`.`renter_id` = `ra`.`renter_id`)) left join `assignments` `asn` on(`r`.`renter_id` = `asn`.`renter_id` and `asn`.`status` = 'Active')) left join `rooms` `rm` on(`asn`.`room_id` = `rm`.`room_id`)) ;

-- --------------------------------------------------------

--
-- Structure for view `vw_renter_utility_bills`
--
DROP TABLE IF EXISTS `vw_renter_utility_bills`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_renter_utility_bills`  AS SELECT `ub`.`bill_id` AS `bill_id`, `ub`.`room_id` AS `room_id`, `rm`.`room_number` AS `room_number`, `ub`.`bill_type` AS `bill_type`, `ub`.`billing_month` AS `billing_month`, `ub`.`previous_reading` AS `previous_reading`, `ub`.`current_reading` AS `current_reading`, `ub`.`consumption` AS `consumption`, `ub`.`amount` AS `total_bill_amount`, `ub`.`amount_per_person` AS `amount_per_person`, `ub`.`billing_date` AS `billing_date`, `ub`.`due_date` AS `due_date`, `ub`.`status` AS `bill_status`, `ub`.`payment_date` AS `payment_date` FROM (`utility_bills` `ub` join `rooms` `rm` on(`ub`.`room_id` = `rm`.`room_id`)) ;

-- --------------------------------------------------------

--
-- Structure for view `vw_room_occupancy_summary`
--
DROP TABLE IF EXISTS `vw_room_occupancy_summary`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_room_occupancy_summary`  AS SELECT `r`.`room_id` AS `room_id`, `r`.`room_number` AS `room_number`, `r`.`floor_level` AS `floor_level`, `r`.`capacity` AS `capacity`, `r`.`occupied` AS `occupied`, `r`.`capacity`- `r`.`occupied` AS `available_slots`, `r`.`status` AS `status`, `r`.`monthly_rate` AS `monthly_rate`, `r`.`photo_path` AS `photo_path` FROM `rooms` AS `r` ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `activity_logs`
--
ALTER TABLE `activity_logs`
  ADD PRIMARY KEY (`log_id`),
  ADD KEY `admin_id` (`admin_id`);

--
-- Indexes for table `admins`
--
ALTER TABLE `admins`
  ADD PRIMARY KEY (`admin_id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `assignments`
--
ALTER TABLE `assignments`
  ADD PRIMARY KEY (`assignment_id`),
  ADD KEY `student_id` (`renter_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `fk_admin_assigned` (`assigned_by`);

--
-- Indexes for table `facility_overview`
--
ALTER TABLE `facility_overview`
  ADD PRIMARY KEY (`facility_id`);

--
-- Indexes for table `maintenance`
--
ALTER TABLE `maintenance`
  ADD PRIMARY KEY (`request_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `fk_maint_staff` (`assigned_staff_id`),
  ADD KEY `fk_maint_renter` (`requester_renter_id`);

--
-- Indexes for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  ADD PRIMARY KEY (`request_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `renter_id` (`renter_id`);

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`payment_id`),
  ADD UNIQUE KEY `invoice_number` (`invoice_number`),
  ADD KEY `student_id` (`renter_id`),
  ADD KEY `fk_payment_admin` (`processed_by`);

--
-- Indexes for table `rental_applications`
--
ALTER TABLE `rental_applications`
  ADD PRIMARY KEY (`application_id`);

--
-- Indexes for table `renters`
--
ALTER TABLE `renters`
  ADD PRIMARY KEY (`renter_id`);

--
-- Indexes for table `renter_accounts`
--
ALTER TABLE `renter_accounts`
  ADD PRIMARY KEY (`account_id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD KEY `renter_id` (`renter_id`);

--
-- Indexes for table `rooms`
--
ALTER TABLE `rooms`
  ADD PRIMARY KEY (`room_id`),
  ADD UNIQUE KEY `room_number` (`room_number`);

--
-- Indexes for table `room_amenities`
--
ALTER TABLE `room_amenities`
  ADD PRIMARY KEY (`amenity_id`),
  ADD KEY `room_id` (`room_id`);

--
-- Indexes for table `staff_payroll`
--
ALTER TABLE `staff_payroll`
  ADD PRIMARY KEY (`payroll_id`),
  ADD KEY `admin_id` (`admin_id`);

--
-- Indexes for table `utility_bills`
--
ALTER TABLE `utility_bills`
  ADD PRIMARY KEY (`bill_id`),
  ADD KEY `room_id` (`room_id`);

--
-- Indexes for table `visitor_logs`
--
ALTER TABLE `visitor_logs`
  ADD PRIMARY KEY (`visitor_id`),
  ADD KEY `renter_id` (`renter_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `activity_logs`
--
ALTER TABLE `activity_logs`
  MODIFY `log_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=47;

--
-- AUTO_INCREMENT for table `admins`
--
ALTER TABLE `admins`
  MODIFY `admin_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `assignments`
--
ALTER TABLE `assignments`
  MODIFY `assignment_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `facility_overview`
--
ALTER TABLE `facility_overview`
  MODIFY `facility_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `maintenance`
--
ALTER TABLE `maintenance`
  MODIFY `request_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  MODIFY `request_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rental_applications`
--
ALTER TABLE `rental_applications`
  MODIFY `application_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `renters`
--
ALTER TABLE `renters`
  MODIFY `renter_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `renter_accounts`
--
ALTER TABLE `renter_accounts`
  MODIFY `account_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `rooms`
--
ALTER TABLE `rooms`
  MODIFY `room_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `room_amenities`
--
ALTER TABLE `room_amenities`
  MODIFY `amenity_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `staff_payroll`
--
ALTER TABLE `staff_payroll`
  MODIFY `payroll_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `utility_bills`
--
ALTER TABLE `utility_bills`
  MODIFY `bill_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `visitor_logs`
--
ALTER TABLE `visitor_logs`
  MODIFY `visitor_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `activity_logs`
--
ALTER TABLE `activity_logs`
  ADD CONSTRAINT `activity_logs_ibfk_1` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`admin_id`);

--
-- Constraints for table `assignments`
--
ALTER TABLE `assignments`
  ADD CONSTRAINT `assignments_ibfk_1` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`),
  ADD CONSTRAINT `assignments_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`),
  ADD CONSTRAINT `fk_admin_assigned` FOREIGN KEY (`assigned_by`) REFERENCES `admins` (`admin_id`),
  ADD CONSTRAINT `fk_assignment_renter_rel` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_renter_assign` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_renter_assign_new` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_room_assign` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_room_assign_new` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `maintenance`
--
ALTER TABLE `maintenance`
  ADD CONSTRAINT `fk_maint_renter` FOREIGN KEY (`requester_renter_id`) REFERENCES `renters` (`renter_id`),
  ADD CONSTRAINT `fk_maint_staff` FOREIGN KEY (`assigned_staff_id`) REFERENCES `admins` (`admin_id`),
  ADD CONSTRAINT `fk_room_maint` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `maintenance_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`);

--
-- Constraints for table `maintenance_requests`
--
ALTER TABLE `maintenance_requests`
  ADD CONSTRAINT `maintenance_requests_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`),
  ADD CONSTRAINT `maintenance_requests_ibfk_2` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`);

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `fk_payment_admin` FOREIGN KEY (`processed_by`) REFERENCES `admins` (`admin_id`),
  ADD CONSTRAINT `fk_payment_renter_rel` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_renter_pay` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`);

--
-- Constraints for table `renter_accounts`
--
ALTER TABLE `renter_accounts`
  ADD CONSTRAINT `renter_accounts_ibfk_1` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`) ON DELETE CASCADE;

--
-- Constraints for table `room_amenities`
--
ALTER TABLE `room_amenities`
  ADD CONSTRAINT `room_amenities_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`) ON DELETE CASCADE;

--
-- Constraints for table `staff_payroll`
--
ALTER TABLE `staff_payroll`
  ADD CONSTRAINT `payroll_ibfk_1` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`admin_id`) ON DELETE CASCADE;

--
-- Constraints for table `utility_bills`
--
ALTER TABLE `utility_bills`
  ADD CONSTRAINT `utility_bills_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`room_id`);

--
-- Constraints for table `visitor_logs`
--
ALTER TABLE `visitor_logs`
  ADD CONSTRAINT `visitor_logs_ibfk_1` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`renter_id`);

DELIMITER $$
--
-- Events
--
CREATE DEFINER=`root`@`localhost` EVENT `ev_mark_overdue_payments` ON SCHEDULE EVERY 1 DAY STARTS '2026-05-04 06:20:11' ON COMPLETION PRESERVE ENABLE DO BEGIN
    UPDATE payments
    SET    status = 'Overdue'
    WHERE  status = 'Pending'
      AND  due_date IS NOT NULL
      AND  due_date < CURRENT_DATE();
END$$

CREATE DEFINER=`root`@`localhost` EVENT `ev_expire_assignments` ON SCHEDULE EVERY 1 DAY STARTS '2026-05-04 06:20:11' ON COMPLETION PRESERVE ENABLE DO BEGIN
    UPDATE assignments
    SET    status = 'Expired'
    WHERE  status = 'Active'
      AND  check_out_date IS NOT NULL
      AND  check_out_date < CURRENT_DATE();
END$$

CREATE DEFINER=`root`@`localhost` EVENT `ev_cleanup_old_visitors` ON SCHEDULE EVERY 30 DAY STARTS '2026-05-04 06:20:11' ON COMPLETION PRESERVE ENABLE DO BEGIN
    DELETE FROM visitor_logs
    WHERE time_out < CURRENT_DATE() - INTERVAL 90 DAY;
END$$

DELIMITER ;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
