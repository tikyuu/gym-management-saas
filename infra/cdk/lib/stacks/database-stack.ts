import {
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_ec2 as ec2,
  aws_logs as logs,
  aws_rds as rds,
  aws_secretsmanager as secretsmanager,
  aws_sns as sns,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseStackProps extends StackProps {
  alertTopic: sns.ITopic;
  applicationName: string;
  databaseAllocatedStorage: number;
  databaseAutoMinorVersionUpgrade: boolean;
  databaseBackupRetentionPeriod: number;
  databaseDeletionProtection: boolean;
  databaseEngineVersion: string;
  databaseInstanceIdentifier: string;
  databaseInstanceClass: string;
  databaseMaxAllocatedStorage: number;
  databaseMultiAz: boolean;
  databaseName: string;
  databasePreferredBackupWindow: string;
  databasePreferredMaintenanceWindow: string;
  databaseRemovalPolicy: RemovalPolicy;
  databaseSubnetIds: string[];
  databaseStorageType: string;
  environmentName: string;
  rdsSecurityGroup: ec2.ISecurityGroup;
}

export class DatabaseStack extends Stack {
  public readonly databaseEndpointAddress: string;
  public readonly databaseEndpointPort: string;
  public readonly masterUserSecretArn: string;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "database");

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    const databaseLogGroup = new logs.LogGroup(this, "DatabaseLogGroup", {
      logGroupName: `/aws/rds/instance/${props.databaseInstanceIdentifier}/postgresql`,
      removalPolicy: props.databaseRemovalPolicy,
      retention: logs.RetentionDays.TWO_MONTHS,
    });

    const databaseSubnetGroup = new rds.CfnDBSubnetGroup(
      this,
      "DatabaseSubnetGroup",
      {
        dbSubnetGroupDescription: "Subnet group for the RDS database",
        dbSubnetGroupName: `${resourceNamePrefix}-db-subnet-group`,
        subnetIds: props.databaseSubnetIds,
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-db-subnet-group`,
          },
        ],
      },
    );

    const databaseInstance = new rds.CfnDBInstance(this, "DatabaseInstance", {
      allocatedStorage: props.databaseAllocatedStorage.toString(),
      autoMinorVersionUpgrade: props.databaseAutoMinorVersionUpgrade,
      backupRetentionPeriod: props.databaseBackupRetentionPeriod,
      deletionProtection: props.databaseDeletionProtection,
      dbInstanceIdentifier: props.databaseInstanceIdentifier,
      dbInstanceClass: props.databaseInstanceClass,
      dbName: props.databaseName,
      dbSubnetGroupName: databaseSubnetGroup.ref,
      engine: "postgres",
      engineVersion: props.databaseEngineVersion,
      enableCloudwatchLogsExports: ["postgresql"],
      manageMasterUserPassword: true,
      masterUsername: "db_admin",
      maxAllocatedStorage: props.databaseMaxAllocatedStorage,
      multiAz: props.databaseMultiAz,
      preferredBackupWindow: props.databasePreferredBackupWindow,
      preferredMaintenanceWindow: props.databasePreferredMaintenanceWindow,
      publiclyAccessible: false,
      storageType: props.databaseStorageType,
      storageEncrypted: true,
      vpcSecurityGroups: [props.rdsSecurityGroup.securityGroupId],
      tags: [
        {
          key: "Name",
          value: props.databaseInstanceIdentifier,
        },
      ],
    });

    databaseInstance.node.addDependency(databaseLogGroup);

    databaseInstance.applyRemovalPolicy(props.databaseRemovalPolicy);

    new rds.CfnEventSubscription(this, "FailureEventSubscription", {
      enabled: true,
      eventCategories: ["failure"],
      snsTopicArn: props.alertTopic.topicArn,
      sourceIds: [databaseInstance.ref],
      sourceType: "db-instance",
      subscriptionName: `${resourceNamePrefix}-rds-failure-events`,
    });

    new secretsmanager.Secret(this, "ApplicationUserSecret", {
      generateSecretString: {
        generateStringKey: "password",
        passwordLength: 32,
        secretStringTemplate: JSON.stringify({ username: "gym_app" }),
      },
      removalPolicy: props.databaseRemovalPolicy,
      secretName: `${resourceNamePrefix}-app-db-credentials`,
    });

    new secretsmanager.Secret(this, "MigrationUserSecret", {
      generateSecretString: {
        generateStringKey: "password",
        passwordLength: 32,
        secretStringTemplate: JSON.stringify({ username: "gym_migrator" }),
      },
      removalPolicy: props.databaseRemovalPolicy,
      secretName: `${resourceNamePrefix}-migration-db-credentials`,
    });

    this.databaseEndpointAddress = databaseInstance.attrEndpointAddress;
    this.databaseEndpointPort = databaseInstance.attrEndpointPort;
    this.masterUserSecretArn =
      databaseInstance.attrMasterUserSecretSecretArn;
  }
}
