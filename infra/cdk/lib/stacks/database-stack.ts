import {
  Stack,
  StackProps,
  aws_ec2 as ec2,
  aws_rds as rds,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseStackProps extends StackProps {
  applicationName: string;
  databaseAllocatedStorage: number;
  databaseEngineVersion: string;
  databaseInstanceClass: string;
  databaseMaxAllocatedStorage: number;
  databaseMultiAz: boolean;
  databaseSubnetIds: string[];
  databaseStorageType: string;
  environmentName: string;
  rdsSecurityGroup: ec2.ISecurityGroup;
  vpc: ec2.IVpc;
}

export class DatabaseStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

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

    new rds.CfnDBInstance(this, "DatabaseInstance", {
      allocatedStorage: props.databaseAllocatedStorage.toString(),
      dbInstanceClass: props.databaseInstanceClass,
      dbSubnetGroupName: databaseSubnetGroup.ref,
      engine: "postgres",
      engineVersion: props.databaseEngineVersion,
      manageMasterUserPassword: true,
      masterUsername: "db_admin",
      maxAllocatedStorage: props.databaseMaxAllocatedStorage,
      multiAz: props.databaseMultiAz,
      publiclyAccessible: false,
      storageType: props.databaseStorageType,
      storageEncrypted: true,
      vpcSecurityGroups: [props.rdsSecurityGroup.securityGroupId],
    });
  }
}
